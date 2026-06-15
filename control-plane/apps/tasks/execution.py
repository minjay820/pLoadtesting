from __future__ import annotations

from rest_framework import serializers


MAX_DURATION_SECONDS = 86_400
SUPPORTED_STOP_POLICIES = {"graceful_stop", "hard_stop"}
FUTURE_STOP_POLICIES = {"drain_inflight", "complete_dataset", "whichever_first"}
SUPPORTED_DATA_POLICIES = {"duration_first", "iteration_first"}

ENGINE_DEFAULT_EXECUTION = {
    "k6": {
        "duration_seconds": 10,
        "ramp_up_seconds": 0,
        "ramp_down_seconds": 0,
        "stop_policy": "graceful_stop",
        "graceful_stop_seconds": 10,
        "max_run_seconds": 30,
        "iteration_limit": None,
        "data_policy": "duration_first",
    },
    "jmeter": {
        "duration_seconds": 20,
        "ramp_up_seconds": 5,
        "ramp_down_seconds": 0,
        "stop_policy": "graceful_stop",
        "graceful_stop_seconds": 10,
        "max_run_seconds": 40,
        "iteration_limit": None,
        "data_policy": "duration_first",
    },
}


def default_execution_for_engine(engine: str) -> dict:
    default = ENGINE_DEFAULT_EXECUTION.get(engine)
    if not default:
        return {}
    return dict(default)


def resolve_execution(engine: str, template_execution: dict | None, request_execution: dict | None) -> dict | None:
    execution = default_execution_for_engine(engine)
    if not execution and template_execution is None and request_execution is None:
        return None
    execution.update(template_execution or {})
    execution.update(request_execution or {})
    return validate_execution(execution)


def validate_execution(execution: dict) -> dict:
    if not isinstance(execution, dict):
        raise serializers.ValidationError({"execution": "Execution must be an object."})

    normalized = dict(execution)

    duration_seconds = _positive_int(normalized, "duration_seconds")
    if duration_seconds > MAX_DURATION_SECONDS:
        raise serializers.ValidationError(
            {"execution": {"duration_seconds": f"Must be less than or equal to {MAX_DURATION_SECONDS}."}}
        )

    for field in ("ramp_up_seconds", "ramp_down_seconds", "graceful_stop_seconds"):
        _non_negative_int(normalized, field)

    iteration_limit = normalized.get("iteration_limit")
    if iteration_limit is not None:
        normalized["iteration_limit"] = _positive_int(normalized, "iteration_limit")

    stop_policy = normalized.get("stop_policy")
    if stop_policy in FUTURE_STOP_POLICIES:
        raise serializers.ValidationError(
            {
                "execution": {
                    "stop_policy": (
                        f"{stop_policy} is planned for future policy support. "
                        f"MVP supports: {', '.join(sorted(SUPPORTED_STOP_POLICIES))}."
                    )
                }
            }
        )
    if stop_policy not in SUPPORTED_STOP_POLICIES:
        raise serializers.ValidationError(
            {"execution": {"stop_policy": f"Unsupported stop_policy. Use one of: {', '.join(sorted(SUPPORTED_STOP_POLICIES))}."}}
        )

    data_policy = normalized.get("data_policy")
    if data_policy not in SUPPORTED_DATA_POLICIES:
        raise serializers.ValidationError(
            {"execution": {"data_policy": f"Unsupported data_policy. Use one of: {', '.join(sorted(SUPPORTED_DATA_POLICIES))}."}}
        )

    max_run_seconds = normalized.get("max_run_seconds")
    if max_run_seconds is not None:
        max_run_seconds = _positive_int(normalized, "max_run_seconds")
        min_required = duration_seconds + normalized["graceful_stop_seconds"]
        if max_run_seconds < min_required:
            raise serializers.ValidationError(
                {
                    "execution": {
                        "max_run_seconds": (
                            "Must be greater than or equal to duration_seconds + graceful_stop_seconds "
                            f"({min_required})."
                        )
                    }
                }
            )
        normalized["max_run_seconds"] = max_run_seconds

    return normalized


def _positive_int(payload: dict, field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or value is None:
        raise serializers.ValidationError({"execution": {field: "Must be a positive integer."}})
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({"execution": {field: "Must be a positive integer."}}) from exc
    if value <= 0:
        raise serializers.ValidationError({"execution": {field: "Must be a positive integer."}})
    payload[field] = value
    return value


def _non_negative_int(payload: dict, field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or value is None:
        raise serializers.ValidationError({"execution": {field: "Must be a non-negative integer."}})
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({"execution": {field: "Must be a non-negative integer."}}) from exc
    if value < 0:
        raise serializers.ValidationError({"execution": {field: "Must be a non-negative integer."}})
    payload[field] = value
    return value
