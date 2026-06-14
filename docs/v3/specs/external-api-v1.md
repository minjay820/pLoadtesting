# External API v1 Planning Spec

This spec defines the intended stable external API shape for future pLoadtesting consumers. It does not change the current runtime API.

## Current Runtime Baseline

The current Control Plane exposes preview endpoints under `/api/`:

- `GET /api/workers/`
- `POST /api/workers/`
- `POST /api/workers/{id}/heartbeat/`
- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/{id}/`
- `GET /api/tasks/templates/`
- `GET /api/tasks/templates/coverage/`
- `POST /api/tasks/{id}/results/`

Worker Agents expose:

- `POST /execute`

Future `/api/v1` routes should wrap these concepts with clearer compatibility guarantees.

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

When `target_app_id` and `target_profile_id` are provided, the API should resolve:

- `engine`
- `script_path`
- `target_url`
- default `parameters`
- default `name`

Client-provided `parameters` should override template defaults only for supported keys. The implementation should document rejected override keys when stricter validation is added.

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

## Template Coverage Contract

The preview endpoint `GET /api/tasks/templates/coverage/` exposes machine-readable coverage metadata for future dashboard consumers. The future v1 equivalent should preserve these concepts:

- `summary`: target count, profile count, engine counts, exact coverage profile count, and gap profile count
- `targets`: per-target aggregates, workload types, protocol, base URL, profile counts, and gap counts
- `profiles`: one row per profile with engine, script path, equivalent profile, `coverage_status`, `coverage_group`, and `coverage_gap`
- `gaps`: profiles whose `coverage_status` is `gap`

`coverage_status` is `exact` when a profile has a reciprocal `equivalent_profile_id` on the opposite engine within the same target app. It is `gap` when no exact equivalent is defined or the reciprocal metadata is invalid. `coverage_group` is a stable grouping key for dashboard display, and `coverage_gap` is null for exact coverage.

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
