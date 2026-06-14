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
| Result summary | nested task result | Show total requests, failure rate, response time percentiles, throughput, and thresholds |
| Observability link | Grafana provisioned dashboards | Open deeper time-series metrics when available |

## Initial User Flows

1. Operator opens the dashboard and checks worker health.
2. Operator selects a target app and target profile from the catalog.
3. Operator reviews default parameters and submits a task.
4. Operator watches task status change through the Control Plane lifecycle.
5. Operator opens task detail after completion and reviews result summary.
6. Operator follows a Grafana link when deeper time-series inspection is needed.

## Non-Goals For This Phase

- Do not implement a frontend application in this planning round.
- Do not choose a frontend framework in this planning round.
- Do not change Control Plane database models.
- Do not introduce public internet exposure assumptions.
- Do not replace Grafana; use Grafana as an optional deeper observability companion.
- Do not create a separate dashboard-specific backend until the external API contract is stable.

## Data Contract Needs

The future dashboard should use the external API v1 contract once implemented. Until then, it can be planned against the current preview endpoints:

- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/{id}/`
- `GET /api/tasks/templates/`
- `GET /api/workers/`

Dashboard work should not rely on direct database access.

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
