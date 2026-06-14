from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from common import capped_repeat

MAX_ECHO_CHARS = 32_768

app = FastAPI(
    title="pLoadtesting Target Suite - Echo API",
    version="1.0.0",
    description="Baseline and echo target for deterministic, low-risk smoke and payload reflection tests.",
)


class EchoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)
    repeat: int = Field(default=1, ge=1, le=8)
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "echo-api"}


@app.get("/api/echo")
async def get_echo(
    message: str = Query(default="hello", min_length=1, max_length=4096),
    repeat: int = Query(default=1, ge=1, le=8),
) -> dict:
    echoed = capped_repeat(message, repeat, max_chars=MAX_ECHO_CHARS)
    return {
        "message": message,
        "repeat": repeat,
        "echo": echoed,
        "length": len(echoed),
    }


@app.post("/api/echo")
async def post_echo(body: EchoRequest) -> dict:
    echoed = capped_repeat(body.message, body.repeat, max_chars=MAX_ECHO_CHARS)
    return {
        "message": body.message,
        "repeat": body.repeat,
        "echo": echoed,
        "length": len(echoed),
        "metadata": body.metadata,
    }

