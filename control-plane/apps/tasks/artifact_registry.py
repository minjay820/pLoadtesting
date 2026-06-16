from __future__ import annotations

from typing import Any

from .artifact_contract import (
    ARTIFACT_MANIFEST_VERSION,
    LEGACY_ARTIFACT_MANIFEST_VERSION,
    sanitize_artifact_metadata,
    validate_artifact_kind,
    validate_artifact_manifest_version,
    validate_artifact_state,
    validate_checksum_sha256,
    validate_object_ref,
)
from .models import LoadTestTask, TaskArtifact


def register_task_artifact(task: LoadTestTask, artifact_metadata: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_task_artifact_metadata(
        task,
        artifact_metadata,
        artifact_manifest_version=ARTIFACT_MANIFEST_VERSION,
    )

    record, _ = TaskArtifact.objects.update_or_create(
        task=task,
        artifact_id=normalized["artifact_id"],
        defaults=normalized,
    )
    return task_artifact_to_item(record)


def register_task_artifacts(task: LoadTestTask, artifact_manifest: Any) -> list[dict[str, Any]]:
    normalized_manifest = normalize_artifact_manifest_payload(artifact_manifest)
    if not normalized_manifest["items"]:
        return []
    return [
        _register_normalized_task_artifact(
            task,
            entry,
            artifact_manifest_version=normalized_manifest["artifact_manifest_version"],
        )
        for entry in normalized_manifest["items"]
    ]


def normalize_artifact_manifest_payload(artifact_manifest: Any) -> dict[str, Any]:
    if artifact_manifest in (None, ""):
        return {
            "artifact_manifest_version": LEGACY_ARTIFACT_MANIFEST_VERSION,
            "items": [],
        }
    if isinstance(artifact_manifest, list):
        return {
            "artifact_manifest_version": LEGACY_ARTIFACT_MANIFEST_VERSION,
            "items": artifact_manifest,
        }
    if not isinstance(artifact_manifest, dict):
        raise ValueError("artifact_manifest must be a list or an object with items.")
    items = artifact_manifest.get("items")
    if items in (None, ""):
        items = []
    if not isinstance(items, list):
        raise ValueError("artifact_manifest.items must be a list.")
    return {
        "artifact_manifest_version": validate_artifact_manifest_version(
            artifact_manifest.get("artifact_manifest_version"),
            allow_legacy_unspecified=True,
        ),
        "items": items,
    }


def normalize_task_artifact_metadata(
    task: LoadTestTask,
    artifact_metadata: dict[str, Any],
    *,
    artifact_manifest_version: str = ARTIFACT_MANIFEST_VERSION,
) -> dict[str, Any]:
    artifact_id = _required_string(artifact_metadata.get("artifact_id"), "artifact_id")
    metadata = sanitize_artifact_metadata(artifact_metadata.get("metadata"))
    if artifact_manifest_version != LEGACY_ARTIFACT_MANIFEST_VERSION:
        metadata = {
            "artifact_manifest_version": artifact_manifest_version,
            **metadata,
        }
    return {
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
        "storage_backend": _optional_string(artifact_metadata.get("storage_backend")) or "",
        "checksum_sha256": validate_checksum_sha256(artifact_metadata.get("checksum_sha256")),
        "expires_at": artifact_metadata.get("expires_at"),
        "provenance_engine": _optional_string(artifact_metadata.get("provenance_engine")) or task.engine,
        "provenance_source": _required_string(artifact_metadata.get("provenance_source"), "provenance_source"),
        "metadata": metadata,
    }


def task_artifact_to_item(record: TaskArtifact) -> dict[str, Any]:
    return {
        "artifact_id": record.artifact_id,
        "kind": record.kind,
        "name": record.name,
        "state": record.state,
        "size_bytes": record.size_bytes,
        "checksum_sha256": record.checksum_sha256 or None,
        "content_type": record.content_type,
        "created_at": record.created_at.isoformat().replace("+00:00", "Z"),
        "download_available": False,
        "download_url": None,
        "provenance": {
            "engine": record.provenance_engine,
            "source": record.provenance_source,
        },
    }


def _register_normalized_task_artifact(
    task: LoadTestTask,
    artifact_metadata: dict[str, Any],
    *,
    artifact_manifest_version: str,
) -> dict[str, Any]:
    normalized = normalize_task_artifact_metadata(
        task,
        artifact_metadata,
        artifact_manifest_version=artifact_manifest_version,
    )
    record, _ = TaskArtifact.objects.update_or_create(
        task=task,
        artifact_id=normalized["artifact_id"],
        defaults=normalized,
    )
    return task_artifact_to_item(record)


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
