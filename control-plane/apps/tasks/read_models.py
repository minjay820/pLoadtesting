from __future__ import annotations

from typing import Any

from .artifact_contract import (
    ARTIFACT_MANIFEST_VERSION,
    ARTIFACT_KIND_ENGINE_OUTPUT,
    ARTIFACT_KIND_HTML_REPORT,
    ARTIFACT_KIND_JTL,
    ARTIFACT_KIND_RAW_LOG,
    ARTIFACT_KIND_STDERR,
    ARTIFACT_KIND_STDOUT,
    ARTIFACT_KIND_SUMMARY_JSON,
    ARTIFACT_KIND_UNKNOWN,
    ARTIFACT_STATE_AVAILABLE,
    ARTIFACT_STATE_EXPIRED,
    ARTIFACT_STATE_EXTERNAL,
    ARTIFACT_STATE_MISSING,
    ARTIFACT_STATE_PLANNED,
)
from .artifact_registry import task_artifact_to_item
from .models import LoadTestTask, TaskArtifact


def _dt(value) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _parameters(task: LoadTestTask) -> dict[str, Any]:
    return task.parameters if isinstance(task.parameters, dict) else {}


def _raw_report(task: LoadTestTask) -> dict[str, Any]:
    result = getattr(task, "result", None)
    if result is None or not isinstance(result.raw_report, dict):
        return {}
    return result.raw_report


def _target_ids(task: LoadTestTask) -> tuple[str | None, str | None]:
    parameters = _parameters(task)
    plan = parameters.get("shard_execution_plan") if isinstance(parameters.get("shard_execution_plan"), dict) else {}
    shards = plan.get("shards") if isinstance(plan.get("shards"), list) else []
    first_shard = shards[0] if shards and isinstance(shards[0], dict) else {}
    return (
        parameters.get("target_app_id") or first_shard.get("target_app_id"),
        parameters.get("target_profile_id") or first_shard.get("target_profile_id"),
    )


def task_history_item(task: LoadTestTask) -> dict[str, Any]:
    target_app_id, target_profile_id = _target_ids(task)
    return {
        "id": str(task.id),
        "status": task.status,
        "target_app_id": target_app_id,
        "target_profile_id": target_profile_id,
        "engine": task.engine,
        "created_at": _dt(task.created_at),
        "updated_at": _dt(task.updated_at),
    }


def task_parameter_summary(task: LoadTestTask) -> dict[str, Any]:
    parameters = _parameters(task)
    visible_keys = sorted(
        key
        for key in parameters
        if key not in {"execution", "distribution", "shard_execution_plan"}
    )
    return {
        "keys": visible_keys,
        "has_execution": isinstance(parameters.get("execution"), dict),
        "has_distribution": isinstance(parameters.get("distribution"), dict),
        "has_shard_execution_plan": isinstance(parameters.get("shard_execution_plan"), dict),
    }


def task_result_status(task: LoadTestTask) -> dict[str, Any]:
    result = getattr(task, "result", None)
    if result is None:
        return {"status": "not_available"}
    return {
        "status": "available",
        "result_id": str(result.id),
        "collected_at": _dt(result.collected_at),
        "thresholds_passed": result.thresholds_passed,
    }


def single_task_shard_read_model(task: LoadTestTask) -> dict[str, Any]:
    return {
        "source": {"status": "ok"},
        "task_id": str(task.id),
        "mode": "single",
        "shards": [],
        "status": "not_applicable",
        "reason": "Task is not configured for manual shard distribution.",
    }


def task_detail_read_model(task: LoadTestTask) -> dict[str, Any]:
    target_app_id, target_profile_id = _target_ids(task)
    parameters = _parameters(task)
    return {
        "source": {"status": "ok"},
        "task": {
            "id": str(task.id),
            "name": task.name,
            "status": task.status,
            "engine": task.engine,
            "script_path": task.script_path,
            "target_url": task.target_url,
            "target_app_id": target_app_id,
            "target_profile_id": target_profile_id,
            "created_at": _dt(task.created_at),
            "updated_at": _dt(task.updated_at),
            "scheduled_at": _dt(task.scheduled_at),
            "started_at": _dt(task.started_at),
            "finished_at": _dt(task.finished_at),
            "error_message": task.error_message,
        },
        "parameters": task_parameter_summary(task),
        "execution": parameters.get("execution") if isinstance(parameters.get("execution"), dict) else {},
        "distribution": parameters.get("distribution") if isinstance(parameters.get("distribution"), dict) else {},
        "result": task_result_status(task),
        "warnings": [],
    }


def _result_provenance(task: LoadTestTask, available: bool) -> dict[str, Any]:
    if not available:
        return {
            "metrics_source": None,
            "engine": task.engine,
            "percentile_policy": None,
        }
    return {
        "metrics_source": "test_result",
        "engine": task.engine,
        "percentile_policy": "engine_reported",
    }


def result_summary_read_model(task: LoadTestTask) -> dict[str, Any]:
    result = getattr(task, "result", None)
    if result is None:
        return {
            "source": {"status": "ok"},
            "task_id": str(task.id),
            "status": "not_available",
            "summary": {
                "total_requests": None,
                "total_errors": None,
                "duration_seconds": None,
                "throughput_rps": None,
            },
            "latency": {
                "avg_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "p99_ms": None,
            },
            "provenance": _result_provenance(task, available=False),
            "thresholds": {
                "passed": None,
                "detail": [],
            },
            "warnings": [
                _warning(
                    "result_summary_not_available",
                    "Result summary is not available for this task yet.",
                )
            ],
        }

    return {
        "source": {"status": "ok"},
        "task_id": str(task.id),
        "status": "available",
        "summary": {
            "total_requests": result.total_requests,
            "total_errors": result.failed_requests,
            "duration_seconds": task.duration_seconds,
            "throughput_rps": result.throughput_rps,
            "error_rate_pct": result.error_rate_pct,
            "collected_at": _dt(result.collected_at),
        },
        "latency": {
            "avg_ms": result.avg_response_ms,
            "p50_ms": None,
            "p95_ms": result.p95_response_ms,
            "p99_ms": result.p99_response_ms,
        },
        "provenance": _result_provenance(task, available=True),
        "thresholds": {
            "passed": result.thresholds_passed,
            "detail": result.thresholds_detail,
        },
        "warnings": [
            _warning(
                "percentiles_engine_reported",
                "Latency percentiles are engine-reported task result values and are not cross-shard merged.",
            ),
            _warning(
                "p50_not_available",
                "P50 latency is not available because the current stored result model does not persist that percentile.",
            ),
        ],
    }


def artifact_metadata_read_model(task: LoadTestTask) -> dict[str, Any]:
    items = _merged_artifact_items(task)
    return {
        "source": {"status": "ok"},
        "contract": {
            "artifact_manifest_version": ARTIFACT_MANIFEST_VERSION,
        },
        "task_id": str(task.id),
        "summary": {
            "count": len(items),
            "available_count": _state_count(items, ARTIFACT_STATE_AVAILABLE),
            "missing_count": _state_count(items, ARTIFACT_STATE_MISSING),
            "planned_count": _state_count(items, ARTIFACT_STATE_PLANNED),
            "expired_count": _state_count(items, ARTIFACT_STATE_EXPIRED),
            "external_count": _state_count(items, ARTIFACT_STATE_EXTERNAL),
        },
        "items": items,
        "warnings": [],
    }


def artifact_download_placeholder_read_model(task: LoadTestTask, artifact_id: str) -> dict[str, Any] | None:
    if artifact_item_for_download(task, artifact_id) is None:
        return None
    return {
        "source": {"status": "ok"},
        "task_id": str(task.id),
        "artifact_id": artifact_id,
        "status": "not_implemented",
        "download_available": False,
        "warnings": [
            _warning(
                "artifact_download_not_implemented",
                "Artifact download is not implemented for this preview route yet.",
            )
        ],
    }


def artifact_not_found_read_model(task: LoadTestTask, artifact_id: str) -> dict[str, Any]:
    return {
        "source": {"status": "error"},
        "task_id": str(task.id),
        "artifact_id": artifact_id,
        "detail": "Artifact not found for this task.",
        "warnings": [
            _warning(
                "artifact_not_found",
                "The requested artifact does not exist for this task.",
            )
        ],
    }


def artifact_item_for_download(task: LoadTestTask, artifact_id: str) -> dict[str, Any] | None:
    items_by_id = {item["artifact_id"]: item for item in _merged_artifact_items(task)}
    return items_by_id.get(artifact_id)


def _state_count(items: list[dict[str, Any]], state: str) -> int:
    return sum(1 for item in items if item["state"] == state)


def _merged_artifact_items(task: LoadTestTask) -> list[dict[str, Any]]:
    derived_items = {item["artifact_id"]: item for item in _derived_artifact_items(task)}
    persisted_items = _persisted_artifact_items(task)
    derived_items.update(persisted_items)
    return [derived_items[artifact_id] for artifact_id in sorted(derived_items)]


def _persisted_artifact_items(task: LoadTestTask) -> dict[str, dict[str, Any]]:
    records = getattr(task, "artifacts", None)
    if records is None:
        queryset = TaskArtifact.objects.filter(task=task)
        return {record.artifact_id: task_artifact_to_item(record) for record in queryset}
    return {
        record.artifact_id: task_artifact_to_item(record)
        for record in records.all()
    }


def _derived_artifact_items(task: LoadTestTask) -> list[dict[str, Any]]:
    if task.engine == LoadTestTask.Engine.K6:
        specs = [
            ("k6-summary-json", ARTIFACT_KIND_SUMMARY_JSON, "summary.json", "application/json"),
            ("k6-stdout", ARTIFACT_KIND_STDOUT, "stdout.txt", "text/plain"),
            ("k6-stderr", ARTIFACT_KIND_STDERR, "stderr.txt", "text/plain"),
            ("k6-engine-output", ARTIFACT_KIND_ENGINE_OUTPUT, "raw-report.json", "application/json"),
            ("k6-html-report", ARTIFACT_KIND_HTML_REPORT, "report.html", "text/html"),
        ]
    elif task.engine == LoadTestTask.Engine.JMETER:
        specs = [
            ("jmeter-jtl", ARTIFACT_KIND_JTL, "results.jtl", "text/csv"),
            ("jmeter-raw-log", ARTIFACT_KIND_RAW_LOG, "jmeter.log", "text/plain"),
            ("jmeter-stdout", ARTIFACT_KIND_STDOUT, "stdout.txt", "text/plain"),
            ("jmeter-stderr", ARTIFACT_KIND_STDERR, "stderr.txt", "text/plain"),
            ("jmeter-engine-output", ARTIFACT_KIND_ENGINE_OUTPUT, "raw-report.json", "application/json"),
            ("jmeter-html-report", ARTIFACT_KIND_HTML_REPORT, "report.html", "text/html"),
        ]
    else:
        specs = [
            ("engine-output", ARTIFACT_KIND_ENGINE_OUTPUT, "raw-report.json", "application/json"),
            ("unknown-artifact", ARTIFACT_KIND_UNKNOWN, "artifact.bin", "application/octet-stream"),
        ]
    return [_artifact_item(task, artifact_id, kind, name, content_type) for artifact_id, kind, name, content_type in specs]


def _artifact_item(
    task: LoadTestTask,
    artifact_id: str,
    kind: str,
    name: str,
    content_type: str,
) -> dict[str, Any]:
    result = getattr(task, "result", None)
    raw_report = _raw_report(task)
    state = ARTIFACT_STATE_PLANNED
    provenance_source = "engine_convention"
    if kind == ARTIFACT_KIND_STDOUT and raw_report.get("stdout") not in (None, ""):
        state = ARTIFACT_STATE_AVAILABLE
        provenance_source = "result_raw_report"
    elif kind == ARTIFACT_KIND_STDERR and raw_report.get("stderr") not in (None, ""):
        state = ARTIFACT_STATE_AVAILABLE
        provenance_source = "result_raw_report"
    elif kind == ARTIFACT_KIND_ENGINE_OUTPUT and raw_report:
        state = ARTIFACT_STATE_AVAILABLE
        provenance_source = "result_raw_report"
    elif result is not None and kind in {
        ARTIFACT_KIND_SUMMARY_JSON,
        ARTIFACT_KIND_JTL,
        ARTIFACT_KIND_RAW_LOG,
    }:
        state = ARTIFACT_STATE_MISSING
        provenance_source = "worker_output"
    return {
        "artifact_id": artifact_id,
        "kind": kind,
        "name": name,
        "state": state,
        "size_bytes": None,
        "checksum_sha256": None,
        "content_type": content_type,
        "created_at": _dt(result.collected_at) if state == ARTIFACT_STATE_AVAILABLE and result is not None else None,
        "download_available": False,
        "download_url": None,
        "provenance": {
            "engine": task.engine,
            "source": provenance_source,
        },
    }
