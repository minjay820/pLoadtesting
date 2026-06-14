from fastapi import FastAPI, HTTPException, Query, Response

from common import DEFAULT_SEED, deterministic_fraction

app = FastAPI(
    title="pLoadtesting Target Suite - Error API",
    version="1.0.0",
    description="Predictable status, flaky, and 429 scenarios with deterministic mode for CI stability.",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "error-api"}


@app.get("/api/status/{code}")
async def status(code: int) -> None:
    if code < 100 or code > 599:
        raise HTTPException(status_code=422, detail="code must be between 100 and 599.")
    raise HTTPException(status_code=code, detail=f"Simulated status {code}")


@app.get("/api/flaky")
async def flaky(
    rate: float = Query(default=0.5, ge=0.0, le=1.0),
    deterministic: bool = Query(default=False),
    seed: int = Query(default=DEFAULT_SEED),
    request_key: str = Query(default="default", min_length=1, max_length=128),
) -> dict:
    value = deterministic_fraction("flaky", request_key, seed) if deterministic else 0.0
    should_fail = deterministic and value < rate
    if should_fail:
        raise HTTPException(
            status_code=503,
            detail={
                "request_key": request_key,
                "rate": rate,
                "seed": seed,
                "deterministic": deterministic,
                "simulated_failure": True,
            },
        )
    return {
        "request_key": request_key,
        "rate": rate,
        "seed": seed,
        "deterministic": deterministic,
        "simulated_failure": False,
    }


@app.get("/api/rate-limit")
async def rate_limit(response: Response, retry_after_seconds: int = Query(default=3, ge=1, le=60)) -> dict:
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after_seconds)
    return {
        "status_code": 429,
        "retry_after_seconds": retry_after_seconds,
        "detail": "Simulated rate limit response",
    }

