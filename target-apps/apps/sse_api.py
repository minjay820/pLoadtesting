import asyncio
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from common import DEFAULT_SEED, deterministic_fraction

MAX_EVENT_COUNT = 100
MAX_INTERVAL_MS = 5_000

app = FastAPI(
    title="pLoadtesting Target Suite - SSE API",
    version="1.0.0",
    description="Finite and deterministic SSE target for streaming workload smoke and performance checks.",
)


def _validate_stream_args(count: int, interval_ms: int) -> None:
    if count < 1 or count > MAX_EVENT_COUNT:
        raise HTTPException(status_code=422, detail=f"count must be between 1 and {MAX_EVENT_COUNT}.")
    if interval_ms < 0 or interval_ms > MAX_INTERVAL_MS:
        raise HTTPException(
            status_code=422,
            detail=f"interval_ms must be between 0 and {MAX_INTERVAL_MS}.",
        )


def _format_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _ticker_value(index: int, seed: int) -> float:
    fraction = deterministic_fraction("sse-ticker", str(index), seed)
    return round(100 + fraction * 10, 4)


async def _stream_events(event_name: str, count: int, interval_ms: int, payload_factory):
    for index in range(count):
        payload = payload_factory(index)
        yield _format_sse(event_name, payload)
        if interval_ms:
            await asyncio.sleep(interval_ms / 1000)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "sse-api"}


@app.get("/api/events")
async def events(
    count: int = Query(default=10, ge=1, le=MAX_EVENT_COUNT),
    interval_ms: int = Query(default=100, ge=0, le=MAX_INTERVAL_MS),
    deterministic: bool = Query(default=True),
    seed: int = Query(default=DEFAULT_SEED),
):
    _validate_stream_args(count, interval_ms)

    async def generator():
        def payload_factory(index: int) -> dict:
            return {
                "sequence": index + 1,
                "kind": "event",
                "deterministic": deterministic,
                "seed": seed,
            }

        async for chunk in _stream_events("message", count, interval_ms, payload_factory):
            yield chunk

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/api/ticker")
async def ticker(
    count: int = Query(default=10, ge=1, le=MAX_EVENT_COUNT),
    interval_ms: int = Query(default=100, ge=0, le=MAX_INTERVAL_MS),
    deterministic: bool = Query(default=True),
    seed: int = Query(default=DEFAULT_SEED),
):
    _validate_stream_args(count, interval_ms)

    async def generator():
        def payload_factory(index: int) -> dict:
            value = _ticker_value(index, seed) if deterministic else float(index + 100)
            return {
                "sequence": index + 1,
                "symbol": "PLT",
                "value": value,
                "deterministic": deterministic,
                "seed": seed,
            }

        async for chunk in _stream_events("ticker", count, interval_ms, payload_factory):
            yield chunk

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/api/progress")
async def progress(
    steps: int = Query(default=10, ge=1, le=MAX_EVENT_COUNT),
    interval_ms: int = Query(default=100, ge=0, le=MAX_INTERVAL_MS),
    deterministic: bool = Query(default=True),
    seed: int = Query(default=DEFAULT_SEED),
):
    _validate_stream_args(steps, interval_ms)

    async def generator():
        def payload_factory(index: int) -> dict:
            return {
                "step": index + 1,
                "steps": steps,
                "progress_pct": round(((index + 1) / steps) * 100, 2),
                "deterministic": deterministic,
                "seed": seed,
            }

        async for chunk in _stream_events("progress", steps, interval_ms, payload_factory):
            yield chunk

    return StreamingResponse(generator(), media_type="text/event-stream")

