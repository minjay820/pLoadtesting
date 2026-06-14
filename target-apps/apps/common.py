import hashlib
import tempfile
import time
from pathlib import Path

from fastapi import HTTPException

DEFAULT_SEED = 17


def deterministic_fraction(namespace: str, key: str, seed: int = DEFAULT_SEED) -> float:
    digest = hashlib.sha256(f"{namespace}|{key}|{seed}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def capped_repeat(value: str, repeat: int, *, max_chars: int) -> str:
    repeated = value * repeat
    if len(repeated) > max_chars:
        raise HTTPException(
            status_code=422,
            detail=f"Expanded payload exceeds safe limit of {max_chars} characters.",
        )
    return repeated


def cpu_burn(iterations: int) -> dict:
    started_at = time.perf_counter()
    acc = 1.0
    for index in range(1, iterations + 1):
        acc = acc * 1.000001 + index * 0.000001
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return {
        "iterations": iterations,
        "elapsed_ms": round(elapsed_ms, 3),
        "checksum": round(acc, 6),
    }


def allocate_memory(mb: int) -> dict:
    started_at = time.perf_counter()
    size_bytes = mb * 1024 * 1024
    block = bytearray(size_bytes)
    for index in range(0, len(block), 4096):
        block[index] = index % 251
    checksum = sum(block[::4096]) % 100000
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return {
        "allocated_mb": mb,
        "allocated_bytes": size_bytes,
        "checksum": checksum,
        "elapsed_ms": round(elapsed_ms, 3),
    }


def io_burn(kb: int) -> dict:
    started_at = time.perf_counter()
    size_bytes = kb * 1024
    payload = (b"ploadtesting-io-block-" * ((size_bytes // 23) + 1))[:size_bytes]
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(payload)
            handle.flush()
            temp_path = Path(handle.name)
        read_back = temp_path.read_bytes()
        checksum = hashlib.sha256(read_back).hexdigest()[:16]
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        return {
            "written_kb": kb,
            "written_bytes": size_bytes,
            "checksum": checksum,
            "elapsed_ms": round(elapsed_ms, 3),
        }
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

