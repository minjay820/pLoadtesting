from fastapi import FastAPI, Query

from common import allocate_memory, cpu_burn, io_burn

app = FastAPI(
    title="pLoadtesting Target Suite - Resource API",
    version="1.0.0",
    description="CPU, memory, and disk I/O simulation with explicit safe upper bounds.",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "resource-api"}


@app.get("/api/cpu")
async def cpu(iterations: int = Query(default=250_000, ge=1, le=2_000_000)) -> dict:
    return cpu_burn(iterations)


@app.get("/api/memory")
async def memory(mb: int = Query(default=8, ge=1, le=64)) -> dict:
    return allocate_memory(mb)


@app.get("/api/io")
async def io(kb: int = Query(default=128, ge=1, le=1024)) -> dict:
    return io_burn(kb)

