# Dashboard Read Model

This planning spec defines the read models a future pLoadtesting dashboard should consume. It does not implement a dashboard or add a frontend stack. The current Control Plane API now includes additive `execution` and manual shard `distribution` objects on task creation.

## Runtime Sources

The dashboard should read through Control Plane APIs only:

- `GET /api/tasks/templates/coverage/`
- `GET /api/tasks/templates/`
- `POST /api/tasks/`
- `GET /api/tasks/`
- `GET /api/tasks/{id}/`
- `GET /api/tasks/{id}/shard-plan/`
- `GET /api/workers/`

Dashboard consumers should not parse Markdown coverage tables and should not read the database directly.

## Phase 6 MVP Boundary

The Phase 6 dashboard MVP should include only these views:

| MVP View | Primary Source | Purpose |
|---|---|---|
| Target Catalog | `GET /api/tasks/templates/coverage/` | Show available target apps, workload types, base URLs, and profile counts |
| Profile Catalog | `GET /api/tasks/templates/`, `GET /api/tasks/templates/coverage/` | Show selectable profiles, engines, scripts, target URLs, and coverage metadata |
| Coverage Matrix | `GET /api/tasks/templates/coverage/` | Show exact/gap coverage by target and profile |
| Create Task Wizard | `GET /api/tasks/templates/`, `POST /api/tasks/` | Create a task from `target_app_id` and `target_profile_id` |

These views are not part of the Phase 6 MVP:

- API Token UI
- Full result artifact browser
- Agent management console
- Settings page
- Multi-user RBAC UI

## Shared Read Model Fields

Dashboard models should keep API field names intact where possible:

| Field | Meaning |
|---|---|
| `target_app_id` | Stable target app identifier from target manifests |
| `target_profile_id` | Stable task profile identifier from task templates |
| `engine` | Execution engine, currently `k6` or `jmeter` |
| `script_path` | Repository-relative engine sample path |
| `target_url` | Default local or configured target URL |
| `equivalent_profile_id` | Reciprocal profile on the opposite engine when exact coverage exists |
| `coverage_status` | `exact` or `gap` |
| `coverage_group` | Stable grouping key for equivalent profiles |
| `coverage_gap` | Null for exact coverage, otherwise a short gap reason |
| `workload_types` | Target workload categories from the manifest |
| `safe_limits` | Bounded target-app safety metadata from the manifest |
| `execution` | Optional profile duration default from `GET /api/tasks/templates/` rows |
| `distribution` | Optional manual shard metadata stored in task `parameters` |
| `shard_execution_plan` | Generated manual shard plan stored in task `parameters` and exposed by shard-plan endpoint |

## Target Catalog

The Target Catalog reads `targets` from `GET /api/tasks/templates/coverage/`.

Required fields:

- `target_app_id`
- `display_name`
- `protocol`
- `base_url`
- `workload_types`
- `profile_count`
- `k6_profile_count`
- `jmeter_profile_count`
- `exact_coverage_profile_count`
- `gap_profile_count`

Empty state: show an empty catalog and a non-blocking message that no manifests or templates are loaded.

Error state: show the API failure and do not fall back to local Markdown parsing.

Refresh behavior: reload the coverage export on user refresh or page load. The current registry is file-backed, so dashboard clients should not assume live updates without a reload.

## Profile Catalog

The Profile Catalog reads `profiles` from `GET /api/tasks/templates/coverage/` and may use `GET /api/tasks/templates/` for the same row-level fields.

Required fields:

- `target_app_id`
- `target_profile_id`
- `display_name`
- `description`
- `engine`
- `script_path`
- `target_url`
- `equivalent_profile_id`
- `workload_types`
- `safe_limits`
- `coverage_status`
- `coverage_group`
- `coverage_gap`

The catalog should allow filtering by target app, engine, workload type, and coverage status.

## Coverage Matrix

The Coverage Matrix reads the full `GET /api/tasks/templates/coverage/` response:

- `summary` for headline counts
- `targets` for per-target rollups
- `profiles` for one row per profile
- `gaps` for gap-only review

`coverage_status=exact` means the profile has a reciprocal `equivalent_profile_id` on the opposite engine within the same target app. `coverage_status=gap` means exact parity is missing or invalid and `coverage_gap` should be shown.

## Create Task Wizard

The Create Task Wizard should create tasks by profile rather than by free-form script path:

1. Load profile rows from `GET /api/tasks/templates/`.
2. Let the user select `target_app_id` and `target_profile_id`.
3. Optionally let the user override documented parameters, `execution` fields, and manual shard `distribution` rows.
4. Submit `POST /api/tasks/`.

Minimum create payload:

```json
{
  "target_app_id": "payload-api",
  "target_profile_id": "payload-k6-download",
  "created_by": "dashboard-preview"
}
```

The wizard should not probe target URLs by itself. Target URLs are controlled runtime inputs and should remain within the operator's authorized environment.

The future wizard can add an `execution` section after the profile selection step because the preview API already accepts it. The default should be `stop_policy=graceful_stop`, with common duration presets such as 10 minutes and 1 hour. For a 1-hour task, the dashboard should explain through field labels and validation state that supported engine assets stop new load at 1 hour and the worker timeout remains the final safety guard.

Manual shard metadata can be represented as a separate `distribution` section. The section should let operators choose single-agent or manual-shard mode, enter agent labels, and attach per-shard dataset source, format, offset, and limit. The dashboard should show `shards` as explicit rows so a 5000-row dataset split into 2000 and 3000 rows is visible before submission.

Planned create-task objects:

| Object | Dashboard Use |
|---|---|
| `execution` | Current single-agent duration, ramp-up, ramp-down, stop policy, grace period, worker timeout, iteration limit, and data policy controls. |
| `distribution` | Manual shard mode plus agent selector labels and dataset partition rows. |
| `shards` | Per-shard id, agent selector labels, dataset source, format, offset, and limit. |
| `result_aggregation` | Read-only shard-plan object that documents summary-only aggregation limits. |

## Run Monitor

Run Monitor is outside the Phase 6 MVP but should later read `GET /api/tasks/` and `GET /api/tasks/{id}/`.

Expected fields include task id, name, engine, script path, target URL, status, worker assignment, timestamps, error message, and nested result summary when available.

Future full distributed runs should show logical task state separately from shard state. The current preview only exposes manual shard metadata and a shard execution plan.

## Result And Artifact Browser

The full artifact browser is outside the Phase 6 MVP. A later implementation may show result summaries from task detail responses, including request totals, failure rate, response-time percentiles, throughput, threshold status, and a raw report reference or inline raw report depending on future artifact storage policy.

For future distributed runs, the browser should show per-agent and per-shard summaries. Total requests and failed requests can be summed, error rate can be recalculated, and throughput should be recalculated over the run time window. Average latency, p95, and p99 must not be presented as global values unless the API provides mergeable samples, histogram buckets, HDR histogram, t-digest, or engine-supported merged output.

## Agent Health

Agent health is outside the Phase 6 MVP. A later implementation may read `GET /api/workers/` for worker id, name, host, port, status, capabilities, active task count, resource snapshot, heartbeat timestamp, and liveness.

## Stability Notes

- The current `/api/` endpoints are preview runtime truth.
- Future `/api/v1` should preserve the dashboard concepts before promising long-term compatibility.
- Clients should treat new response fields as additive.
- Clients should tolerate unknown workload types and safe-limit keys.
- Clients can treat `execution`, `distribution`, `shard_execution_plan`, and `result_aggregation` as additive preview runtime fields. Full distributed scheduling and result-shard persistence remain future work.
