# Task Execution Model

This planning spec defines the future task execution controls for duration-based execution. It does not change the current database schema, worker runtime, task templates, or scheduler behavior.

## Current Runtime Boundary

The current preview runtime can schedule when a task becomes eligible for dispatch through `scheduled_at`, then a Worker Agent runs the selected k6 or JMeter asset until the engine process exits. There is no current Control Plane field for requested run duration, stop policy, or worker-level execution deadline.

Future implementation should add these controls as an explicit `execution` object instead of overloading `parameters`.

## Execution Object

Proposed request shape:

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
    "data_policy": "time_bounded"
  }
}
```

| Field | Type | Purpose |
|---|---|---|
| `duration_seconds` | integer or null | Target steady execution duration after ramp-up. Example: 600 for 10 minutes, 3600 for 1 hour. |
| `ramp_up_seconds` | integer or null | Optional warm-up period for increasing load. |
| `ramp_down_seconds` | integer or null | Optional ramp-down period after new traffic stops. |
| `stop_policy` | string | How the worker should stop after duration, iteration, or data limits are reached. |
| `graceful_stop_seconds` | integer | Maximum time to wait for in-flight requests after stopping new traffic. |
| `max_run_seconds` | integer | Hard worker-level safety deadline covering ramp-up, duration, ramp-down, and grace time. |
| `iteration_limit` | integer or null | Optional total iteration cap. Useful for bounded smoke and dataset-based tasks. |
| `data_policy` | string | Whether task completion is time-bounded, dataset-bounded, or whichever completes first. |

Recommended defaults:

```json
{
  "duration_seconds": null,
  "ramp_up_seconds": 0,
  "ramp_down_seconds": 0,
  "stop_policy": "graceful_stop",
  "graceful_stop_seconds": 30,
  "max_run_seconds": null,
  "iteration_limit": null,
  "data_policy": "time_bounded"
}
```

`graceful_stop` should be the default stop policy because it prevents new load at the requested boundary while still giving in-flight requests a short window to finish and report cleanly.

## Stop Policies

| Policy | Behavior | MVP Status |
|---|---|---|
| `hard_stop` | Stop the engine process as soon as the limit is reached. In-flight requests can be interrupted. | Future fallback for emergency cancellation and worker timeout enforcement. |
| `graceful_stop` | Stop generating new traffic at the limit, wait up to `graceful_stop_seconds`, then force stop if still running. | MVP default. |
| `drain_inflight` | Stop generating new traffic and wait for all in-flight requests without a short grace window unless `max_run_seconds` is reached. | Future extension for low-volume correctness tests. |
| `complete_dataset` | Continue until the assigned dataset shard is exhausted, even if the target duration has passed, subject to `max_run_seconds`. | Future extension for dataset-completeness runs. |
| `whichever_first` | Stop when the first configured bound is reached, such as duration, iteration limit, or dataset exhaustion. | MVP candidate for mixed time and dataset tasks. |

For a 1-hour task, the expected behavior is:

1. The worker starts ramp-up if configured.
2. The worker generates load for `duration_seconds=3600`.
3. At 1 hour, the worker stops producing new traffic.
4. The worker waits up to `graceful_stop_seconds` for in-flight requests.
5. If work is still active after the grace period, the worker force-stops the engine process.
6. The worker returns a result that records whether the stop was clean, forced, timed out, cancelled, or failed.

## Data Policy

| Data Policy | Meaning |
|---|---|
| `time_bounded` | Duration is the primary bound. Dataset rows can be reused or left unused depending on script behavior. |
| `dataset_bounded` | Dataset shard completion is the primary bound. Duration is advisory unless `max_run_seconds` is reached. |
| `iteration_bounded` | Iteration count is the primary bound. |
| `whichever_first` | Stop at the first reached bound among duration, iteration, or dataset completion. |

The MVP should support `time_bounded` and `whichever_first` at the contract level. `dataset_bounded` and `iteration_bounded` can remain future extensions until the worker and scripts expose row-level progress consistently.

## k6 Mapping

Future k6 mapping should prefer native k6 options when possible:

- `duration_seconds` maps to `--duration` or generated `options.duration` for simple constant-load tasks.
- `ramp_up_seconds`, `duration_seconds`, and `ramp_down_seconds` map to k6 `stages` when staged execution is requested.
- `iteration_limit` maps to `--iterations` or scenario `iterations`.
- `graceful_stop_seconds` maps to k6 scenario `gracefulStop` where scenarios are used.
- `max_run_seconds` remains a worker-level subprocess timeout even when k6 has its own duration.

Existing scripts currently hard-code many `duration`, `stages`, or `iterations` values. Runtime implementation should either refactor scripts to read generated options or have the worker generate a wrapper/scenario configuration instead of assuming every script already supports these fields.

## JMeter Mapping

Future JMeter mapping should use properties passed by the worker:

- `duration_seconds` maps to `ThreadGroup.duration` when scheduler mode is enabled.
- `ramp_up_seconds` maps to `ThreadGroup.ramp_time`.
- `iteration_limit` maps to `LoopController.loops` when using loop-bounded execution.
- `graceful_stop_seconds` maps to worker-side graceful shutdown behavior and, where available, JMeter stop/shutdown command behavior.
- `max_run_seconds` remains a worker-level subprocess timeout.

Current JMeter plans mix scheduler-based duration and fixed loop counts. Runtime implementation should standardize property names before enabling dashboard controls globally.

## Worker Timeout Protection

The worker should calculate an effective safety timeout:

```text
effective_timeout_seconds =
  min_non_null(max_run_seconds, ramp_up_seconds + duration_seconds + ramp_down_seconds + graceful_stop_seconds + safety_margin)
```

If `max_run_seconds` is omitted, the worker should derive a bounded timeout for duration-based tasks. If no duration, iteration, or dataset limit is configured, the API should reject the task or require an explicit operational override.

Worker results should include stop metadata:

```json
{
  "execution_status": "completed",
  "stop_reason": "duration_reached",
  "stop_policy": "graceful_stop",
  "forced_stop": false,
  "requested_duration_seconds": 3600,
  "actual_run_seconds": 3618
}
```

## Dashboard Create Task Wizard

The dashboard should expose execution controls as a compact section in the Create Task Wizard:

- Preset duration choices: 10 minutes, 30 minutes, 1 hour, custom.
- Advanced controls: ramp-up, ramp-down, graceful stop seconds, max run seconds.
- Stop policy selector with `graceful_stop` as the default.
- Optional iteration limit for smoke or bounded validation profiles.
- Data policy selector only when a dataset is attached.

The wizard should show that a 1-hour graceful task stops new load at 1 hour, waits for in-flight requests within the grace period, and only then force-stops if required.

## Contract Status

This is a planning contract for future API, dashboard, and worker work. It should be implemented behind tests before any dashboard control is treated as runtime truth.
