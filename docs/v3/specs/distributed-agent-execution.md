# Distributed Agent Execution

This spec defines the Phase 5.9 manual shard distribution metadata MVP and the remaining future distributed execution work. The current implementation validates manual shard metadata, stores it in `LoadTestTask.parameters`, generates a shard execution plan, exposes a read-only shard-plan endpoint, and lets workers pass one shard dataset assignment to k6 or JMeter.

Phase 5.9 does not add shard tables, database migrations, distributed scheduling, worker claim lifecycle, dashboard UI, token-system changes, new target apps, dynamic balancing, or exact percentile merge.

## Current Runtime Boundary

The preview runtime still stores one `LoadTestTask`, dispatches one worker request, and accepts one `TestResult` for that task. A task can now carry planning metadata for manual shards:

- `parameters.distribution`
- `parameters.shard_execution_plan`

The preview endpoint `GET /api/tasks/{id}/shard-plan/` returns the stored plan when a task was created with `distribution`.

## Supported Distribution Object

Current request shape:

```json
{
  "distribution": {
    "mode": "manual_shards",
    "result_merge_policy": "summary_only",
    "shards": [
      {
        "shard_id": "users-a",
        "agent_selector": {
          "labels": ["zone:a", "engine:k6"]
        },
        "dataset": {
          "source": "artifact://datasets/users.csv",
          "format": "csv",
          "offset": 0,
          "limit": 2000
        }
      },
      {
        "shard_id": "users-b",
        "agent_selector": {
          "labels": ["zone:b", "engine:k6"]
        },
        "dataset": {
          "source": "artifact://datasets/users.csv",
          "format": "csv",
          "offset": 2000,
          "limit": 3000
        }
      }
    ]
  }
}
```

Validation rules:

- `mode` must be `manual_shards`.
- `result_merge_policy` must be `summary_only`; omitted values default to `summary_only`.
- `shards` must contain at least one shard.
- `shard_id` must be a non-empty string and unique within the request.
- `agent_selector.labels` defaults to `[]`; when present it must be an array of strings.
- Each shard must include `dataset.source`, `dataset.format`, `dataset.offset`, and `dataset.limit`.
- `dataset.source` must start with `artifact://` or `inline://`; arbitrary local absolute paths are rejected.
- `dataset.format` must be `csv`, `jsonl`, or `json`.
- `dataset.offset` must be an integer greater than or equal to 0.
- `dataset.limit` must be an integer greater than 0.

Hash, weighted, round-robin, range auto-split, and dynamic balancing are future work.

## Shard Execution Plan

The Control Plane generates a plan after the task is saved, so the plan can include the persisted task id:

```json
{
  "task_id": "task-uuid",
  "distribution": {
    "mode": "manual_shards",
    "result_merge_policy": "summary_only",
    "shard_count": 2
  },
  "shards": [
    {
      "shard_id": "users-a",
      "task_id": "task-uuid",
      "target_app_id": "auth-flow-api",
      "target_profile_id": "auth-k6-refresh-flow",
      "engine": "k6",
      "script_path": "engines/k6/target_apps_auth_refresh_flow.js",
      "target_url": "http://127.0.0.1:18086",
      "agent_selector": {
        "labels": ["zone:a", "engine:k6"]
      },
      "dataset": {
        "source": "artifact://datasets/users.csv",
        "format": "csv",
        "offset": 0,
        "limit": 2000
      },
      "execution": {
        "duration_seconds": 600
      }
    }
  ],
  "result_aggregation": {
    "policy": "summary_only",
    "shard_count": 2,
    "completed_shards": 0,
    "failed_shards": 0,
    "total_requests": 0,
    "total_errors": 0,
    "per_shard": []
  }
}
```

`target_app_id` and `target_profile_id` are included when the task is created from a template. Manual tasks expose those fields as `null`.

## Worker Shard Metadata Mapping

The current scheduler does not fan out all shard rows. Worker mapping is enabled for one shard at a time when the worker receives either `parameters.shard` or `parameters.shard_metadata`.

k6 receives:

```text
SHARD_ID=users-a
DATASET_SOURCE=artifact://datasets/users.csv
DATASET_FORMAT=csv
DATASET_OFFSET=0
DATASET_LIMIT=2000
```

JMeter receives:

```text
-Jshard_id=users-a
-Jdataset_source=artifact://datasets/users.csv
-Jdataset_format=csv
-Jdataset_offset=0
-Jdataset_limit=2000
```

Workers also copy shard metadata into `raw_report.shard` for completed and timeout results when shard metadata is present.

## Result Aggregation MVP

The Phase 5.9 result aggregation object is a contract placeholder in the shard execution plan:

```json
{
  "result_aggregation": {
    "policy": "summary_only",
    "shard_count": 2,
    "completed_shards": 0,
    "failed_shards": 0,
    "total_requests": 0,
    "total_errors": 0,
    "per_shard": []
  }
}
```

Aggregation rules:

- `total_requests` can be summed across shard summaries.
- Error counts can be summed across shard summaries.
- Error rate should be recalculated from summed errors divided by summed requests.
- Average latency must not be calculated by directly averaging shard averages.
- p95 and p99 must not be calculated by averaging shard p95 or p99 values.
- Exact percentile aggregation requires raw samples, histogram buckets, HDR histogram, t-digest, or engine-supported merge output.

Phase 5.9 does not create per-shard `TestResult` records or calculate aggregate metrics from multiple posted results.

## Future Distributed Runtime

Future work should add explicit task run, shard, claim, retry, partial success, cancellation, and result-shard storage concepts instead of stretching the current one-task-one-worker flow.

Future lifecycle:

1. Client creates a logical task with execution and distribution metadata.
2. Control Plane creates task-run and shard records.
3. Worker Agents poll or long-poll for claimable shards.
4. A Worker Agent claims one shard when its engine capability, labels, and target reachability match.
5. The agent executes the shard and posts a result shard.
6. Control Plane aggregates shard status into the task run and logical task state.

Future partitioning strategies can include hash, weighted, round-robin, range auto-split, and dynamic balancing after dataset metadata and agent capacity are modeled.

## Contract Status

Manual shard distribution metadata and shard execution plan export are implemented as preview features. Full distributed scheduling, worker claim, shard persistence, retry lifecycle, partial success state, artifact storage, dashboard UI, and exact percentile merge remain future work.
