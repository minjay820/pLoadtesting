from __future__ import annotations

from typing import Any

from .models import LoadTestTask


def _dt(value) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def _warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _parameters(task: LoadTestTask) -> dict[str, Any]:
    return task.parameters if isinstance(task.parameters, dict) else {}


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
                "p90_ms": None,
                "p95_ms": None,
                "p99_ms": None,
                "max_ms": None,
            },
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
            "p90_ms": result.p90_response_ms,
            "p95_ms": result.p95_response_ms,
            "p99_ms": result.p99_response_ms,
            "max_ms": result.max_response_ms,
        },
        "thresholds": {
            "passed": result.thresholds_passed,
            "detail": result.thresholds_detail,
        },
        "warnings": [],
    }


def artifact_metadata_read_model(task: LoadTestTask) -> dict[str, Any]:
    return {
        "source": {"status": "ok"},
        "task_id": str(task.id),
        "summary": {"count": 0},
        "items": [],
        "warnings": [
            _warning(
                "artifacts_not_available",
                "Artifact metadata is not available for this task yet.",
            )
        ],
    }
