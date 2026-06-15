from __future__ import annotations

from rest_framework import serializers


SUPPORTED_DISTRIBUTION_MODES = {"manual_shards"}
SUPPORTED_RESULT_MERGE_POLICIES = {"summary_only"}
SUPPORTED_DATASET_FORMATS = {"csv", "jsonl", "json"}
SAFE_DATASET_SOURCE_PREFIXES = ("artifact://", "inline://")


def validate_distribution(distribution: dict | None) -> dict | None:
    if distribution is None:
        return None
    if not isinstance(distribution, dict):
        raise serializers.ValidationError({"distribution": "Distribution must be an object."})

    mode = distribution.get("mode")
    if mode not in SUPPORTED_DISTRIBUTION_MODES:
        raise serializers.ValidationError(
            {"distribution": {"mode": "MVP supports only manual_shards."}}
        )

    result_merge_policy = distribution.get("result_merge_policy", "summary_only")
    if result_merge_policy not in SUPPORTED_RESULT_MERGE_POLICIES:
        raise serializers.ValidationError(
            {"distribution": {"result_merge_policy": "MVP supports only summary_only."}}
        )

    shards = distribution.get("shards")
    if not isinstance(shards, list) or not shards:
        raise serializers.ValidationError(
            {"distribution": {"shards": "Must contain at least one shard."}}
        )

    normalized_shards = []
    seen_shard_ids = set()
    for index, shard in enumerate(shards):
        normalized = _normalize_shard(shard, index)
        shard_id = normalized["shard_id"]
        if shard_id in seen_shard_ids:
            raise serializers.ValidationError(
                {"distribution": {"shard_id": f"Duplicate shard_id: {shard_id}."}}
            )
        seen_shard_ids.add(shard_id)
        normalized_shards.append(normalized)

    return {
        "mode": mode,
        "result_merge_policy": result_merge_policy,
        "shards": normalized_shards,
    }


def build_shard_execution_plan(
    *,
    task_id: str,
    distribution: dict,
    execution: dict | None,
    engine: str,
    script_path: str,
    target_url: str,
    target_app_id: str | None = None,
    target_profile_id: str | None = None,
) -> dict:
    shard_count = len(distribution["shards"])
    return {
        "task_id": task_id,
        "distribution": {
            "mode": distribution["mode"],
            "result_merge_policy": distribution["result_merge_policy"],
            "shard_count": shard_count,
        },
        "shards": [
            {
                "shard_id": shard["shard_id"],
                "task_id": task_id,
                "target_app_id": target_app_id,
                "target_profile_id": target_profile_id,
                "engine": engine,
                "script_path": script_path,
                "target_url": target_url,
                "agent_selector": shard["agent_selector"],
                "dataset": shard["dataset"],
                "execution": execution or {},
            }
            for shard in distribution["shards"]
        ],
        "result_aggregation": build_result_aggregation_contract(shard_count),
    }


def build_result_aggregation_contract(shard_count: int) -> dict:
    return {
        "policy": "summary_only",
        "shard_count": shard_count,
        "completed_shards": 0,
        "failed_shards": 0,
        "total_requests": 0,
        "total_errors": 0,
        "per_shard": [],
    }


def _normalize_shard(shard: object, index: int) -> dict:
    if not isinstance(shard, dict):
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}]": "Shard must be an object."}}
        )

    shard_id = shard.get("shard_id")
    if not isinstance(shard_id, str) or not shard_id.strip():
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].shard_id": "Must be a non-empty string."}}
        )

    return {
        "shard_id": shard_id,
        "agent_selector": _normalize_agent_selector(shard.get("agent_selector"), index),
        "dataset": _normalize_dataset(shard.get("dataset"), index),
    }


def _normalize_agent_selector(agent_selector: object, index: int) -> dict:
    if agent_selector is None:
        return {"labels": []}
    if not isinstance(agent_selector, dict):
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].agent_selector": "Must be an object."}}
        )

    labels = agent_selector.get("labels", [])
    if not isinstance(labels, list):
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].agent_selector.labels": "Must be a string array."}}
        )
    if not all(isinstance(label, str) for label in labels):
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].agent_selector.labels": "All labels must be strings."}}
        )
    return {"labels": labels}


def _normalize_dataset(dataset: object, index: int) -> dict:
    if not isinstance(dataset, dict):
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].dataset": "Dataset must be an object."}}
        )

    source = dataset.get("source")
    if not isinstance(source, str) or not source.strip():
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].dataset.source": "Must be a non-empty string."}}
        )
    if not source.startswith(SAFE_DATASET_SOURCE_PREFIXES):
        raise serializers.ValidationError(
            {
                "distribution": {
                    f"shards[{index}].dataset.source": "Must start with artifact:// or inline://."
                }
            }
        )

    dataset_format = dataset.get("format")
    if dataset_format not in SUPPORTED_DATASET_FORMATS:
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].dataset.format": "Use csv, jsonl, or json."}}
        )

    offset = _integer_value(dataset.get("offset"), f"shards[{index}].dataset.offset")
    if offset < 0:
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].dataset.offset": "Must be greater than or equal to 0."}}
        )

    limit = _integer_value(dataset.get("limit"), f"shards[{index}].dataset.limit")
    if limit <= 0:
        raise serializers.ValidationError(
            {"distribution": {f"shards[{index}].dataset.limit": "Must be greater than 0."}}
        )

    return {
        "source": source,
        "format": dataset_format,
        "offset": offset,
        "limit": limit,
    }


def _integer_value(value: object, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise serializers.ValidationError({"distribution": {field: "Must be an integer."}})
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({"distribution": {field: "Must be an integer."}}) from exc
