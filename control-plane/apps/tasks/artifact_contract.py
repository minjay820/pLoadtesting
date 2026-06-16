from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse


ARTIFACT_KIND_SUMMARY_JSON = "summary_json"
ARTIFACT_KIND_HTML_REPORT = "html_report"
ARTIFACT_KIND_JTL = "jtl"
ARTIFACT_KIND_RAW_LOG = "raw_log"
ARTIFACT_KIND_STDOUT = "stdout"
ARTIFACT_KIND_STDERR = "stderr"
ARTIFACT_KIND_ENGINE_OUTPUT = "engine_output"
ARTIFACT_KIND_UNKNOWN = "unknown"

ARTIFACT_STATE_PLANNED = "planned"
ARTIFACT_STATE_AVAILABLE = "available"
ARTIFACT_STATE_MISSING = "missing"
ARTIFACT_STATE_EXPIRED = "expired"
ARTIFACT_STATE_EXTERNAL = "external"

ALLOWED_ARTIFACT_KINDS = {
    ARTIFACT_KIND_SUMMARY_JSON,
    ARTIFACT_KIND_HTML_REPORT,
    ARTIFACT_KIND_JTL,
    ARTIFACT_KIND_RAW_LOG,
    ARTIFACT_KIND_STDOUT,
    ARTIFACT_KIND_STDERR,
    ARTIFACT_KIND_ENGINE_OUTPUT,
    ARTIFACT_KIND_UNKNOWN,
}

ALLOWED_ARTIFACT_STATES = {
    ARTIFACT_STATE_PLANNED,
    ARTIFACT_STATE_AVAILABLE,
    ARTIFACT_STATE_MISSING,
    ARTIFACT_STATE_EXPIRED,
    ARTIFACT_STATE_EXTERNAL,
}

ALLOWED_OBJECT_REF_SCHEMES = {"artifact", "object", "external"}
SENSITIVE_METADATA_TOKENS = {
    "secret",
    "token",
    "credential",
    "cookie",
    "session",
    "authorization",
    "api_key",
    "apikey",
}


def validate_artifact_kind(kind: str) -> str:
    if kind not in ALLOWED_ARTIFACT_KINDS:
        raise ValueError(f"Unsupported artifact kind: {kind}")
    return kind


def validate_artifact_state(state: str) -> str:
    if state not in ALLOWED_ARTIFACT_STATES:
        raise ValueError(f"Unsupported artifact state: {state}")
    return state


def validate_object_ref(object_ref: str | None, *, task_id: str | None = None, artifact_id: str | None = None) -> str | None:
    if object_ref in (None, ""):
        return None
    if not isinstance(object_ref, str):
        raise ValueError("object_ref must be a string or null.")
    if ".." in object_ref:
        raise ValueError("object_ref must not contain path traversal segments.")
    if object_ref.startswith("/") or object_ref.startswith("../") or object_ref.startswith("./"):
        raise ValueError("object_ref must not be a local filesystem path.")

    parsed = urlparse(object_ref)
    if parsed.scheme not in ALLOWED_OBJECT_REF_SCHEMES:
        raise ValueError("object_ref must use artifact://, object://, or external://.")
    if parsed.scheme == "file":
        raise ValueError("object_ref must not use file://.")

    if parsed.scheme == "artifact":
        if parsed.netloc != "tasks":
            raise ValueError("artifact:// references must start with artifact://tasks/...")
        parts = parsed.path.lstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError("artifact:// references must include task and artifact identifiers.")
        if task_id is not None and parts[0] != str(task_id):
            raise ValueError("artifact:// task id must match the owning task.")
        if artifact_id is not None and parts[1] != artifact_id:
            raise ValueError("artifact:// artifact id must match artifact_id.")
    return object_ref


def sanitize_artifact_metadata(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be a JSON object.")
    return {str(key): _sanitize_metadata_value(str(key), item) for key, item in value.items()}


def _sanitize_metadata_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(token in lowered for token in SENSITIVE_METADATA_TOKENS):
        raise ValueError(f"metadata key '{key}' is not allowed.")
    if isinstance(value, Mapping):
        return {str(child_key): _sanitize_metadata_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_metadata_value(key, item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise ValueError(f"metadata value for '{key}' is not JSON-safe.")
