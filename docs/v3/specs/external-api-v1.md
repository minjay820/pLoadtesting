# External API v1 Planning Spec

This spec defines the intended stable external API shape for future pLoadtesting consumers. The preview `/api/` runtime already implements duration execution and manual shard distribution metadata as additive task fields, while stable `/api/v1` routes remain future work.

## Current Runtime Baseline

The current Control Plane exposes preview endpoints under `/api/`:

- `GET /api/workers/`
- `POST /api/workers/`
- `POST /api/workers/{id}/heartbeat/`
- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/{id}/`
- `GET /api/tasks/{id}/result-summary/`
- `GET /api/tasks/{id}/artifacts/`
- `GET /api/tasks/{id}/shard-plan/`
- `GET /api/tasks/templates/`
- `GET /api/tasks/templates/coverage/`
- `POST /api/tasks/{id}/results/`

Worker Agents expose:

- `POST /execute`

Future `/api/v1` routes should wrap these concepts with clearer compatibility guarantees.

Preview API consumers should use [API consumer guide](api-consumer-guide.md) for current endpoint examples and [Dashboard read model](dashboard-read-model.md) for dashboard-oriented read models.

## Versioning Goals

- Use `/api/v1/` for stable external consumers.
- Preserve preview `/api/` endpoints until a migration window is documented.
- Keep response fields additive within v1 where possible.
- Use explicit deprecation notes before removing or renaming fields.
- Keep task-template selection as the primary integration point for target app profiles.

## Planned Resource Families

| Resource | Planned Route Family | Current Source |
|---|---|---|
| Tasks | `/api/v1/tasks/` | `LoadTestTask` |
| Task templates | `/api/v1/task-templates/` | `target-apps/task-templates/*.yaml` plus manifests |
| Template coverage | `/api/v1/task-templates/coverage/` | computed registry coverage metadata |
| Workers | `/api/v1/workers/` | `WorkerNode` |
| Results | `/api/v1/tasks/{task_id}/result/` | `TestResult` |
| Artifacts | `/api/v1/tasks/{task_id}/artifacts/` | artifact metadata placeholder |
| Health | `/api/v1/health/` | Control Plane service health |
| Catalog summary | `/api/v1/catalog/` | target manifests and task templates |

## Task Contract

Task creation should support both explicit fields and template-driven fields, matching the current serializer behavior:

- `name`
- `engine`
- `script_path`
- `target_url`
- `parameters`
- `scheduled_at`
- `created_by`
- `target_app_id`
- `target_profile_id`
- `execution`
- `distribution`
- `dataset`

When `target_app_id` and `target_profile_id` are provided, the API should resolve:

- `engine`
- `script_path`
- `target_url`
- default `parameters`
- default `name`

Client-provided `parameters` should override template defaults only for supported keys. The implementation should document rejected override keys when stricter validation is added.

### Task History Read Contract

The preview `GET /api/tasks/` endpoint now returns a read-model envelope:

```json
{
  "source": {
    "status": "ok"
  },
  "summary": {
    "count": 1,
    "limit": 20,
    "total_available": 1
  },
  "items": [
    {
      "id": "task-uuid",
      "status": "pending",
      "target_app_id": "payload-api",
      "target_profile_id": "payload-k6-download",
      "engine": "k6",
      "created_at": "2026-06-15T00:00:00Z",
      "updated_at": "2026-06-15T00:00:00Z"
    }
  ]
}
```

`limit` is supported with a bounded maximum. `status` filtering is supported for the current preview route. Future v1 pagination can add cursor or page references without changing item semantics.

### Task Detail Read Contract

The preview `GET /api/tasks/{id}/` endpoint returns task identity, status, engine, target/profile identifiers when available, parameter summary, execution, distribution, result status, and warnings. This detail contract avoids requiring API consumers to parse internal serializer fields or database relationships.

### Execution Object

The preview `POST /api/tasks/` endpoint accepts an `execution` object for single-agent duration-based execution and stores it in `parameters.execution`. Future v1 task creation should preserve the same shape:

```json
{
  "execution": {
    "duration_seconds": 600,
    "ramp_up_seconds": 30,
    "ramp_down_seconds": 30,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 720,
    "iteration_limit": null,
    "data_policy": "duration_first"
  }
}
```

The current preview runtime supports `stop_policy=graceful_stop|hard_stop` and `data_policy=duration_first|iteration_first`. Planned stop policies such as `drain_inflight`, `complete_dataset`, and `whichever_first` remain future v1 work. For a 1-hour run, `duration_seconds=3600` means supported engine assets stop generating new traffic at 1 hour and the worker timeout remains the final safety guard through `max_run_seconds`.

See [Task execution model](task-execution-model.md) for k6, JMeter, and worker timeout mapping.

### Distribution And Dataset Objects

The preview `POST /api/tasks/` endpoint accepts a `distribution` object for manual shard metadata and stores it in `parameters.distribution`. It also generates `parameters.shard_execution_plan`, which is available through `GET /api/tasks/{id}/shard-plan/`.

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
      }
    ]
  }
}
```

Current preview support is limited to `mode=manual_shards`, `result_merge_policy=summary_only`, `agent_selector.labels`, and per-shard dataset `source`, `format`, `offset`, and `limit`. Dataset source values must use `artifact://` or `inline://`. Dataset formats are `csv`, `jsonl`, and `json`.

Full shard lifecycle, worker claim, retry, partial success, cancellation, artifact storage, hash partitioning, weighted partitioning, round-robin partitioning, and dynamic balancing remain future work.

### POST /api/v1/tasks Examples

Single agent, 10 minutes:

```json
{
  "target_app_id": "payload-api",
  "target_profile_id": "payload-k6-download",
  "created_by": "api-v1-client",
  "execution": {
    "duration_seconds": 600,
    "ramp_up_seconds": 30,
    "ramp_down_seconds": 30,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 720,
    "iteration_limit": null,
    "data_policy": "duration_first"
  }
}
```

Single agent, 1 hour graceful stop:

```json
{
  "target_app_id": "latency-api",
  "target_profile_id": "latency-jmeter-delay",
  "created_by": "api-v1-client",
  "execution": {
    "duration_seconds": 3600,
    "ramp_up_seconds": 120,
    "ramp_down_seconds": 60,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 60,
    "max_run_seconds": 3900,
    "iteration_limit": null,
    "data_policy": "duration_first"
  }
}
```

Manual shard metadata, 5000 rows split into 2000 and 3000:

```json
{
  "target_app_id": "db-api",
  "target_profile_id": "db-k6-list-filter",
  "created_by": "api-v1-client",
  "execution": {
    "duration_seconds": 1800,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 2100,
    "data_policy": "duration_first"
  },
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

Manual shard metadata, different target network labels:

```json
{
  "target_app_id": "payload-api",
  "target_profile_id": "payload-jmeter-download",
  "created_by": "api-v1-client",
  "execution": {
    "duration_seconds": 900,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 1020,
    "data_policy": "duration_first"
  },
  "distribution": {
    "mode": "manual_shards",
    "result_merge_policy": "summary_only",
    "shards": [
      {
        "shard_id": "network-a",
        "agent_selector": {
          "labels": ["zone:a", "engine:jmeter"]
        },
        "dataset": {
          "source": "artifact://datasets/payload.csv",
          "format": "csv",
          "offset": 0,
          "limit": 1000
        }
      },
      {
        "shard_id": "network-b",
        "agent_selector": {
          "labels": ["zone:b", "engine:jmeter"]
        },
        "dataset": {
          "source": "artifact://datasets/payload.csv",
          "format": "csv",
          "offset": 1000,
          "limit": 1000
        }
      }
    ]
  }
}
```

## Result Contract

Result responses should expose summary fields already represented by `TestResult`:

- total and failed requests
- error rate
- average and percentile response times
- max response time
- throughput
- peak virtual users
- threshold pass/fail status
- threshold detail
- raw report reference or inline raw report, depending on future storage size policy

The current model stores `raw_report` inline. A future artifact store can move large raw output without changing the summary contract.

Shard plan responses include a `result_aggregation` contract object:

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

`total_requests` and error counts can be summed. Error rate can be recalculated from those sums. Average latency must not be directly averaged across shards. p95 and p99 must not be averaged across agents; correct percentile aggregation requires raw samples, histogram buckets, HDR histogram, t-digest, or engine-supported merge output.

### Result Summary Read Contract

The preview `GET /api/tasks/{id}/result-summary/` endpoint maps existing `TestResult` fields into:

- `summary.total_requests`
- `summary.total_errors`
- `summary.duration_seconds`
- `summary.throughput_rps`
- `summary.error_rate_pct`
- `latency.avg_ms`
- `latency.p50_ms`
- `latency.p95_ms`
- `latency.p99_ms`
- `provenance.metrics_source`
- `provenance.engine`
- `provenance.percentile_policy`
- additive `thresholds`

If no result exists, `status` is `not_available`, metric fields are `null`, `provenance` is still present, and `warnings` includes `result_summary_not_available`. API consumers should handle that response as an ordinary task lifecycle state.

`latency.p50_ms` is currently `null` because the stored result model does not provide a p50 field. Core must not invent missing percentile values.

Stored task percentiles are engine-reported values for one task result only. Core must not average shard `p95` or `p99` values. Exact global percentile merge requires raw samples, histogram buckets, HDR histogram, t-digest, or engine-supported merge output.

### Artifact Metadata Read Contract

The preview `GET /api/tasks/{id}/artifacts/` endpoint returns a stable metadata envelope:

```json
{
  "source": {
    "status": "ok"
  },
  "task_id": "task-uuid",
  "summary": {
    "count": 5,
    "available_count": 0,
    "missing_count": 0
  },
  "items": [
    {
      "artifact_id": "k6-summary-json",
      "kind": "summary_json",
      "name": "summary.json",
      "state": "planned",
      "size_bytes": null,
      "content_type": "application/json",
      "created_at": null,
      "download_available": false,
      "download_url": null,
      "provenance": {
        "engine": "k6",
        "source": "engine_convention"
      }
    }
  ],
  "warnings": []
}
```

Current artifact kinds are `summary_json`, `html_report`, `jtl`, `raw_log`, `stdout`, `stderr`, `engine_output`, and `unknown`.

Current artifact states are `planned`, `available`, `missing`, `expired`, and `external`.

`stdout` and `stderr` are `available` only when they are already persisted inside `TestResult.raw_report`. `engine_output` is `available` only when a stored `raw_report` exists. Engine-convention file rows such as `summary_json`, `jtl`, and `raw_log` remain `planned` before result callback and can become `missing` after result callback when Core has no persisted evidence for them.

`download_available` remains `false` and `download_url` remains `null` in this phase.

### Artifact Download Placeholder Contract

The preview `GET /api/tasks/{id}/artifacts/{artifact_id}/download/` endpoint can return structured `501 not implemented` metadata.

The route must not:

- download a real worker-local file
- expose a worker-local path
- accept arbitrary filesystem input

Future download support should use controlled task and artifact identifiers, with signed URLs or external object storage only after a durable artifact store exists.

## Template Coverage Contract

The preview endpoint `GET /api/tasks/templates/coverage/` exposes machine-readable coverage metadata for future dashboard consumers. The future v1 equivalent should preserve these concepts:

- `summary`: target count, profile count, engine counts, exact coverage profile count, and gap profile count
- `targets`: per-target aggregates, workload types, protocol, base URL, profile counts, and gap counts
- `profiles`: one row per profile with engine, script path, equivalent profile, `coverage_status`, `coverage_group`, and `coverage_gap`
- `gaps`: profiles whose `coverage_status` is `gap`

`coverage_status` is `exact` when a profile has a reciprocal `equivalent_profile_id` on the opposite engine within the same target app. It is `gap` when no exact equivalent is defined or the reciprocal metadata is invalid. `coverage_group` is a stable grouping key for dashboard display, and `coverage_gap` is null for exact coverage.

Dashboard and API consumers should treat this endpoint as the source of truth for profile coverage metadata and should not parse Markdown coverage matrices. The current response shape is documented in [API consumer guide](api-consumer-guide.md), with representative examples in [examples/templates-coverage-response.json](examples/templates-coverage-response.json).

## Filtering And Pagination

The first v1 API should support these filters where feasible:

- task status
- engine
- worker id
- created time range
- scheduled time range
- target app id when created from a template
- target profile id when created from a template

Paginated list responses should include:

- total count
- next page reference
- previous page reference
- ordered results

## Error Shape

External API v1 should normalize errors into a consistent object:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {}
  }
}
```

Implementation can map existing DRF validation errors into this shape during the v1 build-out.

## Compatibility Rules

- Existing preview endpoints remain unchanged until a migration plan is accepted.
- v1 endpoints should not expose internal-only fields that are not useful to external consumers.
- Worker registration and result callback endpoints should be separated from dashboard/user-facing scopes.
- The API must not run load tests against third-party targets by default; target URLs remain caller-provided and operationally controlled.

## Open Implementation Questions

- Whether v1 should initially be a thin route alias over current serializers or a separate serializer layer.
- Whether raw reports should stay inline for v1 or be moved behind artifact references first.
- Whether task creation should allow arbitrary `script_path` for external consumers or require manifest-driven templates by default.
- How long preview-only duration and distribution fields should remain before a persisted shard schema is added.
- Which histogram or engine-native output format should be the first supported global percentile merge source.
