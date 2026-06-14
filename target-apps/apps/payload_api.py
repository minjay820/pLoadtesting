import hashlib
import io
import tarfile
import zipfile

from fastapi import Body, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

MAX_DOWNLOAD_KB = 512
MAX_UPLOAD_BYTES = 262_144
MAX_FILE_KB = 256
MAX_FILE_MANIFEST_COUNT = 20
MAX_FILENAME_LENGTH = 64
MAX_ARCHIVE_FILE_COUNT = 10
MAX_ARCHIVE_KB_PER_FILE = 64
MAX_SELECTIVE_FETCH_COUNT = 8

app = FastAPI(
    title="pLoadtesting Target Suite - Payload API",
    version="1.0.0",
    description="Controlled upload and download payload tests with deterministic filler content.",
)


class SelectiveFetchRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=MAX_SELECTIVE_FETCH_COUNT)
    kb_per_file: int = Field(default=12, ge=1, le=MAX_ARCHIVE_KB_PER_FILE)


def _make_download_text(kb: int) -> str:
    target_bytes = kb * 1024
    chunk = ("ploadtesting-payload-block-" * 64).encode("utf-8")
    return (chunk * ((target_bytes // len(chunk)) + 1))[:target_bytes].decode("utf-8", errors="ignore")


def _make_file_bytes(file_id: str, kb: int) -> bytes:
    target_bytes = kb * 1024
    chunk = f"ploadtesting-file|{file_id}|".encode("utf-8") * 128
    return (chunk * ((target_bytes // len(chunk)) + 1))[:target_bytes]


def _fixture_pack_files(count: int, kb_per_file: int) -> list[dict]:
    return [
        {
            "file_id": f"fixture-{index + 1}",
            "filename": f"fixture-{index + 1}.bin",
            "size_kb": kb_per_file,
        }
        for index in range(count)
    ]


def _validate_file_id(file_id: str, *, require_fixture_prefix: bool = False) -> None:
    if len(file_id) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=422, detail=f"file_id exceeds safe limit of {MAX_FILENAME_LENGTH} characters.")
    if require_fixture_prefix:
        if not file_id.startswith("fixture-"):
            raise HTTPException(status_code=422, detail="file_id must start with fixture-.")
        suffix = file_id.split("-", 1)[1]
        if not suffix.isdigit():
            raise HTTPException(status_code=422, detail="file_id must end with a numeric suffix.")


def _validated_selective_file_ids(file_ids: list[str]) -> list[str]:
    if len(file_ids) < 1 or len(file_ids) > MAX_SELECTIVE_FETCH_COUNT:
        raise HTTPException(
            status_code=422,
            detail=f"selected file count must be between 1 and {MAX_SELECTIVE_FETCH_COUNT}.",
        )
    deduped: list[str] = []
    seen: set[str] = set()
    for file_id in file_ids:
        _validate_file_id(file_id, require_fixture_prefix=True)
        if file_id in seen:
            raise HTTPException(status_code=422, detail=f"duplicate file_id is not allowed: {file_id}.")
        seen.add(file_id)
        deduped.append(file_id)
    return deduped


def _fixture_pack_metadata(file_ids: list[str], kb_per_file: int) -> list[dict]:
    return [
        {
            "file_id": file_id,
            "filename": f"{file_id}.bin",
            "size_kb": kb_per_file,
        }
        for file_id in file_ids
    ]


def _pack_id(namespace: str, file_ids: list[str], kb_per_file: int) -> str:
    normalized = ",".join(file_ids)
    return hashlib.sha256(f"{namespace}|{normalized}|{kb_per_file}".encode("utf-8")).hexdigest()[:16]


def _validate_archive_args(count: int, kb_per_file: int) -> None:
    if count > MAX_ARCHIVE_FILE_COUNT:
        raise HTTPException(
            status_code=422,
            detail=f"archive count exceeds safe limit of {MAX_ARCHIVE_FILE_COUNT}.",
        )
    if kb_per_file > MAX_ARCHIVE_KB_PER_FILE:
        raise HTTPException(
            status_code=422,
            detail=f"archive kb_per_file exceeds safe limit of {MAX_ARCHIVE_KB_PER_FILE}.",
        )


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
        "files": _fixture_pack_files(count, kb_per_file),
    }


@app.get("/api/files/fixture-pack")
async def fixture_pack(
    count: int = Query(default=4, ge=1, le=MAX_ARCHIVE_FILE_COUNT),
    kb_per_file: int = Query(default=12, ge=1, le=MAX_ARCHIVE_KB_PER_FILE),
) -> dict:
    _validate_archive_args(count, kb_per_file)
    file_ids = [fixture["file_id"] for fixture in _fixture_pack_files(count, kb_per_file)]
    files = _fixture_pack_metadata(file_ids, kb_per_file)
    pack_id = _pack_id("fixture-pack", file_ids, kb_per_file)
    return {
        "pack_id": pack_id,
        "count": count,
        "kb_per_file": kb_per_file,
        "total_bytes": count * kb_per_file * 1024,
        "files": files,
    }


@app.get("/api/files/archive")
async def file_archive(
    count: int = Query(default=4, ge=1, le=MAX_ARCHIVE_FILE_COUNT),
    kb_per_file: int = Query(default=12, ge=1, le=MAX_ARCHIVE_KB_PER_FILE),
) -> Response:
    _validate_archive_args(count, kb_per_file)
    archive_stream = io.BytesIO()
    file_ids = [fixture["file_id"] for fixture in _fixture_pack_files(count, kb_per_file)]
    pack_id = _pack_id("fixture-pack", file_ids, kb_per_file)
    with zipfile.ZipFile(archive_stream, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for fixture in _fixture_pack_metadata(file_ids, kb_per_file):
            archive.writestr(fixture["filename"], _make_file_bytes(fixture["file_id"], kb_per_file))
    archive_bytes = archive_stream.getvalue()
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="fixture-pack-{pack_id}.zip"',
            "X-Archive-File-Count": str(count),
            "X-Archive-KB-Per-File": str(kb_per_file),
        },
    )


@app.get("/api/files/read-many")
async def read_many(
    count: int = Query(default=6, ge=1, le=MAX_ARCHIVE_FILE_COUNT),
    kb_per_file: int = Query(default=8, ge=1, le=MAX_ARCHIVE_KB_PER_FILE),
) -> dict:
    _validate_archive_args(count, kb_per_file)
    files = []
    combined = hashlib.sha256()
    total_bytes = 0
    for fixture in _fixture_pack_files(count, kb_per_file):
        payload = _make_file_bytes(fixture["file_id"], kb_per_file)
        combined.update(payload)
        total_bytes += len(payload)
        files.append(
            {
                **fixture,
                "sha256_prefix": hashlib.sha256(payload).hexdigest()[:16],
            }
        )
    return {
        "count": count,
        "kb_per_file": kb_per_file,
        "total_bytes": total_bytes,
        "combined_sha256_prefix": combined.hexdigest()[:16],
        "files": files,
    }


@app.get("/api/files/tar-package")
async def tar_package(
    count: int = Query(default=4, ge=1, le=MAX_ARCHIVE_FILE_COUNT),
    kb_per_file: int = Query(default=12, ge=1, le=MAX_ARCHIVE_KB_PER_FILE),
    file_ids: list[str] | None = Query(default=None),
) -> Response:
    if file_ids:
        selected_file_ids = _validated_selective_file_ids(file_ids)
    else:
        _validate_archive_args(count, kb_per_file)
        selected_file_ids = [fixture["file_id"] for fixture in _fixture_pack_files(count, kb_per_file)]

    archive_stream = io.BytesIO()
    pack_id = _pack_id("tar-package", selected_file_ids, kb_per_file)
    with tarfile.open(fileobj=archive_stream, mode="w") as archive:
        for fixture in _fixture_pack_metadata(selected_file_ids, kb_per_file):
            payload = _make_file_bytes(fixture["file_id"], kb_per_file)
            info = tarfile.TarInfo(name=fixture["filename"])
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    archive_bytes = archive_stream.getvalue()
    return Response(
        content=archive_bytes,
        media_type="application/x-tar",
        headers={
            "Content-Disposition": f'attachment; filename="fixture-pack-{pack_id}.tar"',
            "X-Tar-File-Count": str(len(selected_file_ids)),
            "X-Tar-KB-Per-File": str(kb_per_file),
        },
    )


@app.post("/api/files/selective-fetch")
async def selective_fetch(body: SelectiveFetchRequest) -> dict:
    selected_file_ids = _validated_selective_file_ids(body.file_ids)
    files = []
    combined = hashlib.sha256()
    total_bytes = 0
    for fixture in _fixture_pack_metadata(selected_file_ids, body.kb_per_file):
        payload = _make_file_bytes(fixture["file_id"], body.kb_per_file)
        combined.update(payload)
        total_bytes += len(payload)
        files.append(
            {
                **fixture,
                "sha256_prefix": hashlib.sha256(payload).hexdigest()[:16],
                "download_path": f"/api/files/{fixture['file_id']}?kb={body.kb_per_file}",
            }
        )
    return {
        "selected_count": len(selected_file_ids),
        "kb_per_file": body.kb_per_file,
        "total_bytes": total_bytes,
        "combined_sha256_prefix": combined.hexdigest()[:16],
        "files": files,
    }


@app.get("/api/files/{file_id}")
async def file_download(
    file_id: str,
    kb: int = Query(default=32, ge=1, le=MAX_FILE_KB),
    disposition: str = Query(default="attachment", pattern="^(attachment|inline)$"),
) -> Response:
    _validate_file_id(file_id)
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
