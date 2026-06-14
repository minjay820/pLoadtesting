from fastapi import FastAPI, Body, HTTPException, Query, Response

MAX_DOWNLOAD_KB = 512
MAX_UPLOAD_BYTES = 262_144

app = FastAPI(
    title="pLoadtesting Target Suite - Payload API",
    version="1.0.0",
    description="Controlled upload and download payload tests with deterministic filler content.",
)


def _make_download_text(kb: int) -> str:
    target_bytes = kb * 1024
    chunk = ("ploadtesting-payload-block-" * 64).encode("utf-8")
    return (chunk * ((target_bytes // len(chunk)) + 1))[:target_bytes].decode("utf-8", errors="ignore")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "payload-api"}


@app.get("/api/download")
async def download(kb: int = Query(default=32, ge=1, le=MAX_DOWNLOAD_KB)) -> Response:
    payload = _make_download_text(kb)
    return Response(
        content=payload,
        media_type="text/plain",
        headers={"X-Payload-KB": str(kb)},
    )


@app.post("/api/upload")
async def upload(body: str = Body(..., media_type="text/plain")) -> dict:
    byte_size = len(body.encode("utf-8"))
    if byte_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Upload body exceeds safe limit of {MAX_UPLOAD_BYTES} bytes.",
        )
    return {"received_bytes": byte_size, "received_chars": len(body)}

