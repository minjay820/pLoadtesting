import asyncio
import json
from collections import defaultdict

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect

from common import DEFAULT_SEED

MAX_MESSAGE_SIZE = 1_024
MAX_MESSAGES_PER_CONNECTION = 10
MAX_CONCURRENT_CONNECTIONS = 20
MAX_ROOM_SIZE = 5
IDLE_TIMEOUT_SECONDS = 5

app = FastAPI(
    title="pLoadtesting Target Suite - WebSocket API",
    version="1.0.0",
    description="Bounded WebSocket echo and broadcast target for local and CI-safe connection lifecycle validation.",
)

_active_connections = 0
_active_lock = asyncio.Lock()
_rooms: dict[str, set[WebSocket]] = defaultdict(set)
_room_lock = asyncio.Lock()
_room_sequences: dict[str, int] = defaultdict(int)


def _json_dump(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"))


async def _try_acquire_connection() -> bool:
    global _active_connections
    async with _active_lock:
        if _active_connections >= MAX_CONCURRENT_CONNECTIONS:
            return False
        _active_connections += 1
        return True


async def _release_connection() -> None:
    global _active_connections
    async with _active_lock:
        _active_connections = max(_active_connections - 1, 0)


async def _receive_bounded_text(websocket: WebSocket) -> str:
    text = await asyncio.wait_for(websocket.receive_text(), timeout=IDLE_TIMEOUT_SECONDS)
    if len(text) > MAX_MESSAGE_SIZE:
        await websocket.close(code=1009, reason=f"message exceeds {MAX_MESSAGE_SIZE} bytes")
        raise WebSocketDisconnect(code=1009)
    return text


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "target_app_id": "ws-api",
        "active_connections": _active_connections,
    }


@app.websocket("/ws/echo")
async def ws_echo(
    websocket: WebSocket,
    deterministic: bool = Query(default=True),
    seed: int = Query(default=DEFAULT_SEED),
):
    if not await _try_acquire_connection():
        await websocket.close(code=1013, reason="max concurrent connections reached")
        return

    await websocket.accept()
    messages_seen = 0
    try:
        await websocket.send_text(
            _json_dump(
                {
                    "event": "welcome",
                    "mode": "echo",
                    "deterministic": deterministic,
                    "seed": seed,
                    "max_messages": MAX_MESSAGES_PER_CONNECTION,
                }
            )
        )
        while messages_seen < MAX_MESSAGES_PER_CONNECTION:
            payload = await _receive_bounded_text(websocket)
            messages_seen += 1
            await websocket.send_text(
                _json_dump(
                    {
                        "event": "echo",
                        "sequence": messages_seen,
                        "message": payload,
                        "deterministic": deterministic,
                        "seed": seed,
                    }
                )
            )
        await websocket.send_text(_json_dump({"event": "limit-reached", "sequence": messages_seen}))
        await websocket.close(code=1000, reason="max messages reached")
    except asyncio.TimeoutError:
        await websocket.close(code=1001, reason="idle timeout")
    except WebSocketDisconnect:
        pass
    finally:
        await _release_connection()


@app.websocket("/ws/broadcast/{room}")
async def ws_broadcast(
    websocket: WebSocket,
    room: str,
    client_id: str = Query(default="client"),
    deterministic: bool = Query(default=True),
    seed: int = Query(default=DEFAULT_SEED),
):
    if not await _try_acquire_connection():
        await websocket.close(code=1013, reason="max concurrent connections reached")
        return

    await websocket.accept()
    added_to_room = False
    messages_seen = 0
    try:
        async with _room_lock:
            peers = _rooms[room]
            if len(peers) >= MAX_ROOM_SIZE:
                await websocket.close(code=1013, reason="max room size reached")
                return
            peers.add(websocket)
            added_to_room = True
            room_size = len(peers)

        await websocket.send_text(
            _json_dump(
                {
                    "event": "welcome",
                    "mode": "broadcast",
                    "room": room,
                    "client_id": client_id,
                    "room_size": room_size,
                    "deterministic": deterministic,
                    "seed": seed,
                }
            )
        )

        while messages_seen < MAX_MESSAGES_PER_CONNECTION:
            message = await _receive_bounded_text(websocket)
            messages_seen += 1
            async with _room_lock:
                _room_sequences[room] += 1
                sequence = _room_sequences[room]
                peers = list(_rooms[room])
            payload = _json_dump(
                {
                    "event": "broadcast",
                    "room": room,
                    "sender": client_id,
                    "sequence": sequence,
                    "message": message,
                    "deterministic": deterministic,
                    "seed": seed,
                }
            )
            for peer in peers:
                await peer.send_text(payload)

        await websocket.send_text(_json_dump({"event": "limit-reached", "sequence": messages_seen}))
        await websocket.close(code=1000, reason="max messages reached")
    except asyncio.TimeoutError:
        await websocket.close(code=1001, reason="idle timeout")
    except WebSocketDisconnect:
        pass
    finally:
        if added_to_room:
            async with _room_lock:
                peers = _rooms.get(room)
                if peers is not None:
                    peers.discard(websocket)
                    if not peers:
                        _rooms.pop(room, None)
                        _room_sequences.pop(room, None)
        await _release_connection()
