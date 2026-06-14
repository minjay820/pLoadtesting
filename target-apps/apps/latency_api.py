import asyncio

from fastapi import FastAPI, HTTPException, Query

MAX_DELAY_MS = 5_000
TIMEOUT_THRESHOLD_MS = 2_000

app = FastAPI(
    title="pLoadtesting Target Suite - Latency API",
    version="1.0.0",
    description="Delay and timeout-style target with explicit safe caps for local and CI use.",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "latency-api"}


@app.get("/api/delay/{ms}")
async def delay(ms: int) -> dict:
    if ms < 0 or ms > MAX_DELAY_MS:
        raise HTTPException(status_code=422, detail=f"ms must be between 0 and {MAX_DELAY_MS}.")
    await asyncio.sleep(ms / 1000)
    return {"requested_delay_ms": ms, "applied_delay_ms": ms, "timed_out": False}


@app.get("/api/timeout-simulation")
async def timeout_simulation(ms: int = Query(default=2500, ge=0, le=MAX_DELAY_MS)) -> dict:
    await asyncio.sleep(ms / 1000)
    if ms >= TIMEOUT_THRESHOLD_MS:
        raise HTTPException(
            status_code=504,
            detail={
                "requested_delay_ms": ms,
                "timed_out": True,
                "timeout_threshold_ms": TIMEOUT_THRESHOLD_MS,
            },
        )
    return {
        "requested_delay_ms": ms,
        "timed_out": False,
        "timeout_threshold_ms": TIMEOUT_THRESHOLD_MS,
    }

