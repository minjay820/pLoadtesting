from __future__ import annotations

from typing import Any

from .artifact_contract import (
    sanitize_artifact_metadata,
    validate_artifact_kind,
    validate_artifact_state,
    validate_object_ref,
)
from .models import LoadTestTask, TaskArtifact


def register_task_artifact(task: LoadTestTask, artifact_metadata: dict[str, Any]) -> dict[str, Any]:
    artifact_id = _required_string(artifact_metadata.get("artifact_id"), "artifact_id")
    normalized = {
        "artifact_id": artifact_id,
        "kind": validate_artifact_kind(_required_string(artifact_metadata.get("kind"), "kind")),
        "name": _required_string(artifact_metadata.get("name"), "name"),
        "state": validate_artifact_state(_required_string(artifact_metadata.get("state"), "state")),
        "size_bytes": _optional_int(artifact_metadata.get("size_bytes")),
        "content_type": _optional_string(artifact_metadata.get("content_type")),
        "object_ref": validate_object_ref(
            _optional_string(artifact_metadata.get("object_ref")),
            task_id=str(task.id),
            artifact_id=artifact_id,
        ),
        "storage_backend": _optional_string(artifact_metadata.get("storage_backend")),
        "checksum_sha256": _optional_string(artifact_metadata.get("checksum_sha256")),
        "expires_at": artifact_metadata.get("expires_at"),
        "provenance_engine": _optional_string(artifact_metadata.get("provenance_engine")) or task.engine,
        "provenance_source": _required_string(artifact_metadata.get("provenance_source"), "provenance_source"),
        "metadata": sanitize_artifact_metadata(artifact_metadata.get("metadata")),
    }

    record, _ = TaskArtifact.objects.update_or_create(
        task=task,
        artifact_id=artifact_id,
        defaults=normalized,
    )
    return task_artifact_to_item(record)


def task_artifact_to_item(record: TaskArtifact) -> dict[str, Any]:
    return {
        "artifact_id": record.artifact_id,
        "kind": record.kind,
        "name": record.name,
        "state": record.state,
        "size_bytes": record.size_bytes,
        "content_type": record.content_type,
        "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
        "download_available": False,
        "download_url": None,
        "provenance": {
            "engine": record.provenance_engine,
            "source": record.provenance_source,
        },
    }


def _required_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("Optional string fields must be strings when provided.")
    return value


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("size_bytes must be an integer when provided.")
    if value < 0:
        raise ValueError("size_bytes must be non-negative.")
    return value
