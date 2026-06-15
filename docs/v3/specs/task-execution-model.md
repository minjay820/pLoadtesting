# Task Execution Model

This spec defines the current duration-based execution MVP, worker timeout protection, and shard metadata mapping. Phase 5.9 adds manual shard distribution metadata and dataset partition metadata without adding database schema, distributed scheduling, dashboard UI, token-system changes, or new target apps.

## Current Runtime Boundary

The preview Control Plane accepts an additive write-only `execution` object on `POST /api/tasks/`. The serializer normalizes validated execution metadata into the existing `LoadTestTask.parameters["execution"]` object, so task responses expose it through the existing `parameters` field.

Execution precedence is:

1. Request `execution` override.
2. Profile template `execution` default.
3. Engine default execution.

The worker reads `parameters["execution"]` only when present. Existing tasks without this object keep the previous subprocess command shape and do not receive a worker timeout from the new helper path.

## Execution Object

Current request shape:

```json
{
  "execution": {
    "duration_seconds": 600,
    "ramp_up_seconds": 60,
    "ramp_down_seconds": 30,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 720,
    "iteration_limit": null,
    "data_policy": "duration_first"
  }
}
```

| Field | Type | Purpose |
|---|---|---|
| `duration_seconds` | integer | Target execution duration. Example: 600 for 10 minutes, 3600 for 1 hour. |
| `ramp_up_seconds` | integer | Optional warm-up period for increasing load. |
| `ramp_down_seconds` | integer | Optional ramp-down period after steady execution. |
| `stop_policy` | string | Runtime-supported values are `graceful_stop` and `hard_stop`. |
| `graceful_stop_seconds` | integer | Maximum grace window for engines or worker timeout metadata. |
| `max_run_seconds` | integer or null | Worker-level subprocess timeout. |
| `iteration_limit` | integer or null | Optional total iteration cap for bounded validation. |
| `data_policy` | string | Runtime-supported values are `duration_first` and `iteration_first`. |

Engine defaults:

```json
{
  "k6": {
    "duration_seconds": 10,
    "ramp_up_seconds": 0,
    "ramp_down_seconds": 0,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 10,
    "max_run_seconds": 30,
    "iteration_limit": null,
    "data_policy": "duration_first"
  },
  "jmeter": {
    "duration_seconds": 20,
    "ramp_up_seconds": 5,
    "ramp_down_seconds": 0,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 10,
    "max_run_seconds": 40,
    "iteration_limit": null,
    "data_policy": "duration_first"
  }
}
```

Validation rules:

- `duration_seconds` must be a positive integer and cannot exceed `86400`.
- `ramp_up_seconds`, `ramp_down_seconds`, and `graceful_stop_seconds` must be non-negative integers.
- `max_run_seconds`, when provided, must be at least `duration_seconds + graceful_stop_seconds`.
- `stop_policy` must be `graceful_stop` or `hard_stop`; planned policies such as `drain_inflight`, `complete_dataset`, and `whichever_first` are rejected with future-policy messaging.
- `data_policy` must be `duration_first` or `iteration_first`.

## Stop Policies

| Policy | Behavior | Status |
|---|---|---|
| `graceful_stop` | Stop generating new traffic at the requested boundary when the engine asset supports graceful scenario control; worker timeout remains the final guard. | Supported in the MVP contract and representative assets. |
| `hard_stop` | Use the worker subprocess timeout as the hard safety boundary. In-flight work can be interrupted if the process exceeds `max_run_seconds`. | Supported in the MVP contract. |
| `drain_inflight` | Stop new traffic and wait for all in-flight work without a short grace window unless `max_run_seconds` is reached. | Future extension. |
| `complete_dataset` | Continue until the assigned dataset shard is exhausted, subject to `max_run_seconds`. | Future extension. |
| `whichever_first` | Stop when the first configured bound is reached, such as duration, iteration limit, or dataset exhaustion. | Future extension. |

For a 1-hour graceful task, the current intended behavior is:

1. The worker passes duration metadata to the supported k6/JMeter asset.
2. The engine generates load for `duration_seconds=3600`, with ramp-up or ramp-down where the asset supports it.
3. New load stops at the engine duration boundary.
4. The worker subprocess timeout remains active through `max_run_seconds`.
5. If the process exceeds the timeout, the worker posts a failed result with `raw_report.error=worker_timeout`, stop metadata, stdout, and stderr.

## Data Policy

| Data Policy | Meaning | Status |
|---|---|---|
| `duration_first` | Duration is the primary bound. Dataset rows can be reused or left unused depending on script behavior. | Supported in the MVP contract. |
| `iteration_first` | Iteration count is the primary bound when `iteration_limit` is provided. | Supported in the MVP contract and representative k6 helper. |

Dataset-bounded and whichever-first data semantics remain future work. Phase 5.9 supports dataset partition metadata for manual shards, but workers do not load or track row-level dataset progress.

## k6 Mapping

The worker passes these environment variables to k6 when `parameters["execution"]` is present:

- `DURATION_SECONDS`
- `RAMP_UP_SECONDS`
- `RAMP_DOWN_SECONDS`
- `GRACEFUL_STOP_SECONDS`
- `ITERATION_LIMIT`
- `STOP_POLICY`
- `DATA_POLICY`

When a worker receives one shard through `parameters["shard"]` or `parameters["shard_metadata"]`, it also passes:

- `SHARD_ID`
- `DATASET_SOURCE`
- `DATASET_FORMAT`
- `DATASET_OFFSET`
- `DATASET_LIMIT`

The helper at `engines/k6/lib/execution.js` builds k6 `options` from these values. Phase 5.8 updates exactly these representative scripts to use the helper:

- `engines/k6/target_apps_payload_download.js`
- `engines/k6/target_apps_echo_smoke.js`
- `engines/k6/target_apps_latency_delay.js`
- `engines/k6/target_apps_auth_checkout.js`

Other k6 assets continue using their existing hard-coded options until follow-up coverage expands.

## JMeter Mapping

The worker passes matching JMeter properties when `parameters["execution"]` is present:

- `-Jduration_seconds`
- `-Jramp_up_seconds`
- `-Jramp_down_seconds`
- `-Jstop_policy`
- `-Jgraceful_stop_seconds`
- `-Jiteration_limit`

When a worker receives one shard through `parameters["shard"]` or `parameters["shard_metadata"]`, it also passes:

- `-Jshard_id`
- `-Jdataset_source`
- `-Jdataset_format`
- `-Jdataset_offset`
- `-Jdataset_limit`

Phase 5.8 updates these representative plans to read duration and ramp-up properties:

- `engines/jmeter/target_apps_echo_latency_plan.jmx`
- `engines/jmeter/target_apps_payload_crud_plan.jmx`
- `engines/jmeter/target_apps_auth_flow_plan.jmx`

Other JMeter plans continue using their existing settings until follow-up coverage expands.

## Worker Timeout Protection

When execution metadata is present, the worker calculates an effective subprocess timeout:

```text
effective_timeout_seconds =
  max_run_seconds
  OR duration_seconds + ramp_up_seconds + ramp_down_seconds + graceful_stop_seconds + safety_margin
```

The current API defaults always provide `max_run_seconds`. If no execution object is present, the worker keeps the previous unbounded subprocess behavior for compatibility.

Timeout results are posted with the existing failed task state, not a new database state:

```json
{
  "execution_status": "failed",
  "error_message": "Engine process exceeded max_run_seconds (690).",
  "raw_report": {
    "error": "worker_timeout",
    "stop_reason": "worker_timeout",
    "forced_stop": true,
    "timeout_seconds": 690,
    "execution": {
      "duration_seconds": 600
    }
  }
}
```

## Dashboard Create Task Wizard

Dashboard implementation is not part of Phase 5.9. A future dashboard wizard can expose execution controls because the preview API now accepts and returns `parameters.execution`.

The wizard should show:

- Preset duration choices: 10 minutes, 30 minutes, 1 hour, custom.
- Advanced controls: ramp-up, ramp-down, graceful stop seconds, max run seconds.
- Stop policy selector limited to `graceful_stop` and `hard_stop` until future policies are implemented.
- Optional iteration limit for bounded validation profiles.
- Data policy selector limited to `duration_first` and `iteration_first` until dataset runtime exists.
- Optional manual shard rows with `agent_selector.labels` and dataset `source`, `format`, `offset`, and `limit`.

## Contract Status

Duration-based execution and manual shard metadata are implemented as additive preview API and worker runtime features. Full distributed scheduling, dataset loading, advanced stop policies, dashboard UI, and long-term `/api/v1` compatibility remain future work.
