import hashlib

from fastapi import Body, FastAPI, HTTPException, Query, Response

MAX_DOWNLOAD_KB = 512
MAX_UPLOAD_BYTES = 262_144
MAX_FILE_KB = 256
MAX_FILE_MANIFEST_COUNT = 20
MAX_FILENAME_LENGTH = 64

app = FastAPI(
    title="pLoadtesting Target Suite - Payload API",
    version="1.0.0",
    description="Controlled upload and download payload tests with deterministic filler content.",
)


def _make_download_text(kb: int) -> str:
    target_bytes = kb * 1024
    chunk = ("ploadtesting-payload-block-" * 64).encode("utf-8")
    return (chunk * ((target_bytes // len(chunk)) + 1))[:target_bytes].decode("utf-8", errors="ignore")


def _make_file_bytes(file_id: str, kb: int) -> bytes:
    target_bytes = kb * 1024
    chunk = f"ploadtesting-file|{file_id}|".encode("utf-8") * 128
    return (chunk * ((target_bytes // len(chunk)) + 1))[:target_bytes]


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


@app.get("/api/files/manifest")
async def file_manifest(
    count: int = Query(default=5, ge=1, le=MAX_FILE_MANIFEST_COUNT),
    kb_per_file: int = Query(default=16, ge=1, le=MAX_FILE_KB),
) -> dict:
    return {
        "count": count,
        "kb_per_file": kb_per_file,
        "files": [
            {
                "file_id": f"fixture-{index + 1}",
                "filename": f"fixture-{index + 1}.bin",
                "size_kb": kb_per_file,
            }
            for index in range(count)
        ],
    }


@app.get("/api/files/{file_id}")
async def file_download(
    file_id: str,
    kb: int = Query(default=32, ge=1, le=MAX_FILE_KB),
    disposition: str = Query(default="attachment", pattern="^(attachment|inline)$"),
) -> Response:
    if len(file_id) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=422, detail=f"file_id exceeds safe limit of {MAX_FILENAME_LENGTH} characters.")
    payload = _make_file_bytes(file_id, kb)
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'{disposition}; filename="{file_id}.bin"',
            "X-File-KB": str(kb),
            "X-File-Id": file_id,
        },
    )


@app.post("/api/files/upload")
async def file_upload(
    body: bytes = Body(..., media_type="application/octet-stream"),
    filename: str = Query(default="upload.bin", min_length=1, max_length=MAX_FILENAME_LENGTH),
) -> dict:
    byte_size = len(body)
    if byte_size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Upload body exceeds safe limit of {MAX_UPLOAD_BYTES} bytes.",
        )
    return {
        "filename": filename,
        "received_bytes": byte_size,
        "sha256_prefix": hashlib.sha256(body).hexdigest()[:16],
    }
