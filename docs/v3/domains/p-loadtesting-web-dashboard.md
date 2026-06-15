# pLoadtesting Web Dashboard Plan

This document defines the future dashboard direction for pLoadtesting. It is a planning document only; no dashboard implementation is included in this phase.

## Purpose

The dashboard should provide a reader and operator interface over existing Control Plane concepts:

- task creation and task history
- task template and target profile catalog
- worker health and capacity status
- result summaries and threshold outcomes
- links or embeds for existing Grafana observability views

The dashboard should reduce manual API usage without changing the Control Plane task, worker, or result lifecycle.

## MVP Views

| View | Primary Data Source | Purpose |
|---|---|---|
| Task list | `GET /api/tasks/` | Show queued, dispatched, running, completed, and failed work |
| Task detail | `GET /api/tasks/{id}/` | Show task configuration, worker assignment, status, result summary, and error message |
| Run creation | `GET /api/tasks/templates/`, `POST /api/tasks/` | Create tasks from manifest-driven target profiles |
| Worker health | `GET /api/workers/` | Show worker online/offline state, active task count, and capabilities |
| Target profile catalog | `GET /api/tasks/templates/` | Expose available target apps, profiles, engines, scripts, and parity metadata |
| Coverage matrix | `GET /api/tasks/templates/coverage/` | Read machine-readable profile coverage status and target aggregates |
| Result summary | nested task result | Show total requests, failure rate, response time percentiles, throughput, and thresholds |
| Observability link | Grafana provisioned dashboards | Open deeper time-series metrics when available |

## Phase 6 MVP Boundary

The Phase 6 dashboard MVP should be limited to:

- Target Catalog
- Profile Catalog
- Coverage Matrix
- Create Task Wizard

The following views and controls should remain outside the Phase 6 MVP:

- API Token UI
- Full result artifact browser
- Agent management console
- Settings page
- Multi-user RBAC UI

The implementation-facing read model for these views is defined in [Dashboard read model](../specs/dashboard-read-model.md).

Execution duration controls and manual shard distribution metadata are now available as preview API/runtime fields, but no dashboard UI is implemented in this phase. Full distributed execution controls remain planned follow-on work. The dashboard should read the contracts in [Task execution model](../specs/task-execution-model.md) and [Distributed agent execution](../specs/distributed-agent-execution.md), and it should not expose scheduler controls that the runtime cannot enforce.

## Initial User Flows

1. Operator opens the dashboard and checks worker health.
2. Operator selects a target app and target profile from the catalog.
3. Operator reviews default parameters and submits a task.
4. Operator watches task status change through the Control Plane lifecycle.
5. Operator opens task detail after completion and reviews result summary.
6. Operator follows a Grafana link when deeper time-series inspection is needed.

Future duration and distribution flows:

1. Operator selects a duration preset such as 10 minutes or 1 hour.
2. Operator keeps the default `graceful_stop` stop policy or chooses `hard_stop`.
3. Operator optionally switches from single-agent to manual-shard metadata mode.
4. Operator assigns shard rows to agent selector labels and dataset ranges.
5. Operator reviews the generated shard execution plan before submission or after task creation.

## Non-Goals For This Phase

- Do not implement a frontend application in this planning round.
- Do not choose a frontend framework in this planning round.
- Do not change Control Plane database models.
- Do not introduce public internet exposure assumptions.
- Do not replace Grafana; use Grafana as an optional deeper observability companion.
- Do not create a separate dashboard-specific backend until the external API contract is stable.
- Do not present distributed p95 or p99 as global metrics unless the API marks the percentile aggregation method as mergeable.

## Data Contract Needs

The future dashboard should use the external API v1 contract once implemented. Until then, it can be planned against the current preview endpoints:

- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/{id}/`
- `GET /api/tasks/templates/`
- `GET /api/tasks/templates/coverage/`
- `GET /api/workers/`

Dashboard work should not rely on direct database access.

The dashboard should use `GET /api/tasks/templates/coverage/` for coverage cards, parity filters, and target/profile counts instead of parsing Markdown coverage documents. `coverage_status=exact` indicates reciprocal k6/JMeter pairing, while `coverage_status=gap` indicates a profile that should be shown with a gap explanation from `coverage_gap`.

API consumers should follow [API consumer guide](../specs/api-consumer-guide.md) for current preview endpoint examples and should treat future `/api/v1` routes as a compatibility target rather than current runtime behavior.

API objects should appear in dashboard models as additive fields:

- `execution` for the current single-agent duration, ramp, stop policy, grace period, timeout, iteration limit, and data policy.
- `distribution` for manual shard metadata mode.
- `shards` for agent selector labels, dataset source, dataset format, offset, and limit.
- `shard_execution_plan` for previewing the generated shard plan.
- `result_aggregation` for summary-only aggregation limits and future global summary quality.

## Safety And Access

- Dashboard access must not weaken the current Control Plane access boundary.
- Any write action must require an access scope that permits task creation.
- Worker registration and result callback operations should not be available from ordinary dashboard sessions.
- Links to target URLs must be displayed as configured values, not automatically probed by the dashboard.

## Future Implementation Sequence

1. Stabilize external API v1 read endpoints.
2. Add scoped access for dashboard read and task-create operations.
3. Build a minimal read-only dashboard over tasks, workers, results, and templates.
4. Add task creation through target profiles.
5. Add Grafana deep links or embeds only after deployment access boundaries are documented.
