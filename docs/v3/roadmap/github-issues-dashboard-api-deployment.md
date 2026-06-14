# Dashboard, API, And Distributed Deployment Issue Drafts

These drafts are ready to copy into GitHub issues when the team decides to open tracked work. They intentionally stay as repository documentation in this phase.

## Issue 1: Build Dashboard MVP Over Existing Control Plane APIs

**Summary**

Create a minimal dashboard that reads tasks, workers, results, and task templates from the Control Plane.

**Problem / Use Case**

Operators currently need direct API calls to inspect task state, worker health, available target profiles, and result summaries.

**Proposed Solution**

Build a dashboard MVP with task list/detail, worker health, target profile catalog, result summary, and run creation from existing templates.

**Expected Behavior**

Users can create a template-driven task and inspect the task lifecycle without using manual API calls.

**Acceptance Criteria**

- Dashboard reads task templates from the Control Plane.
- Dashboard can list tasks and open task detail.
- Dashboard can show worker online/offline state and active task count.
- Dashboard can show result summary fields after task completion.
- Dashboard does not require direct database access.

**Validation**

- Dashboard tests cover template listing, task list, worker list, and task detail rendering.
- Manual smoke validates a low-cost target profile task.

**Dependencies**

- External API v1 read contract or documented preview API adapter.
- Scoped dashboard access plan.

## Issue 2: Define And Implement External API v1

**Summary**

Add stable `/api/v1` endpoints for tasks, task templates, workers, results, health, and catalog summary.

**Problem / Use Case**

The current preview `/api/` routes work for local development but do not define a compatibility contract for dashboard and automation consumers.

**Proposed Solution**

Create a versioned API layer that preserves current concepts while normalizing pagination, errors, filtering, and response shapes.

**Expected Behavior**

External clients can integrate with `/api/v1` without relying on preview route details.

**Acceptance Criteria**

- `/api/v1/tasks/` supports list, create, and detail.
- `/api/v1/task-templates/` exposes target profile catalog metadata.
- `/api/v1/workers/` exposes worker state for readers.
- `/api/v1/tasks/{id}/result/` exposes result summary.
- Error responses follow the documented v1 shape.

**Validation**

- Django API tests cover success and validation-error paths.
- Existing preview endpoints continue to pass current tests.

**Dependencies**

- `docs/v3/specs/external-api-v1.md`.

## Issue 3: Add Scoped API Access

**Summary**

Implement scoped API access to replace the current all-or-nothing shared preview access over time.

**Problem / Use Case**

Dashboard users, automation clients, Worker Agents, and administrators should not share the same broad access capability.

**Proposed Solution**

Add scoped access verification with separate read, write, worker, result, and administration scopes.

**Expected Behavior**

Routes reject callers that do not have the required scope while preserving a documented local-preview migration path.

**Acceptance Criteria**

- Access values are stored as verifiers, not raw values.
- Route families declare required scopes.
- Worker registration and result callback scopes are separated from dashboard scopes.
- Tests cover allowed, denied, expired, and revoked access paths.

**Validation**

- Django tests cover each route family and scope decision.
- Logs do not print raw access values.

**Dependencies**

- `docs/v3/specs/api-token-auth.md`.
- External API v1 route decisions.

## Issue 4: Harden Three-Host Distributed Deployment

**Summary**

Turn the distributed deployment runbook into tested deployment support for Control Plane plus two Worker Agent hosts.

**Problem / Use Case**

The current architecture supports remote workers conceptually, but cross-host deployment needs clear validation, configuration, and failure handling.

**Proposed Solution**

Add deployment examples, health checks, and validation scripts for a Control Plane host and two Worker hosts in a controlled internal network.

**Expected Behavior**

Operators can validate registration, heartbeat, dispatch, result callback, and target reachability across hosts.

**Acceptance Criteria**

- Runbook commands are validated in a controlled lab environment.
- Worker advertised address and Control Plane dispatch behavior are documented.
- Failure modes for pending tasks, offline workers, dispatch errors, and missing results are covered.
- Rollback steps are tested.

**Validation**

- Manual cross-host smoke run.
- Low-cost k6 and JMeter template tasks complete from both workers.

**Dependencies**

- `docs/v3/runbooks/distributed-deployment.md`.
- Scoped access hardening before any public exposure.

## Issue 5: Add Dashboard And API Test Coverage

**Summary**

Add tests that protect future dashboard and external API behavior.

**Problem / Use Case**

Once a dashboard and stable API exist, regressions in task template listing, task creation, worker state, and result summary can break user-facing flows.

**Proposed Solution**

Create tests for API response contracts and dashboard integration points before broad feature expansion.

**Expected Behavior**

API and dashboard regressions are caught in CI before merge.

**Acceptance Criteria**

- API contract tests cover tasks, templates, workers, and results.
- Dashboard tests cover read-only rendering and task creation form behavior.
- Tests use local fixtures and do not require external services.

**Validation**

- CI runs the new test suites.
- Existing target-app and Control Plane tests continue to pass.

**Dependencies**

- Dashboard MVP implementation.
- External API v1 implementation.

## Issue 6: Public Project Documentation Readiness

**Summary**

Prepare contributor-facing documentation so the project can be understood, validated, and extended without private context.

**Problem / Use Case**

The project now has several active docs areas, target catalogs, and validation paths. Contributors need a clear entry path and safety boundaries.

**Proposed Solution**

Tighten README pointers, docs/v3 indexes, validation command summaries, and safety notes without removing legacy docs prematurely.

**Expected Behavior**

New contributors can find the active docs trunk, run local validations, and understand target-app safety constraints.

**Acceptance Criteria**

- Root README points to the active docs trunk.
- docs/v3 indexes expose current domains, specs, runbooks, and roadmap.
- Validation commands are consistent across README, runbooks, and CI.
- Safety boundaries stay prominent.

**Validation**

- Link review over changed docs.
- Existing validation commands continue to pass.

**Dependencies**

- Current docs/v3 governance.

## Issue 7: Maintain Profile Coverage Metadata

**Summary**

Keep target profile coverage metadata accurate as new profiles are added or existing profiles change.

**Problem / Use Case**

The dashboard and API consumers depend on reciprocal `equivalent_profile_id` metadata and the coverage export to avoid parsing Markdown matrices.

**Proposed Solution**

Require every new current-catalog profile to either define exact reciprocal parity or explicitly document a gap through registry metadata and tests.

**Expected Behavior**

The coverage matrix and machine-readable coverage export remain explicit and auditable.

**Acceptance Criteria**

- New exact pairs have reciprocal `equivalent_profile_id` metadata.
- Coverage summary counts in docs match template metadata.
- `GET /api/tasks/templates/coverage/` reflects current exact and gap counts.
- Dashboard consumers can show exact and gap states without Markdown parsing.

**Validation**

- `target-apps/tests/test_suite.py` parity validation passes.
- Control Plane template coverage export tests pass.

**Dependencies**

- Existing target profile coverage matrix.

## Issue 8: Add Duration-Based Task Execution Model

**Title**

Add duration-based task execution model

**Labels**

- `area:api`
- `area:worker`
- `type:contract`

**Problem**

Tasks can currently schedule when dispatch starts, but they do not have a first-class contract for running 10 minutes, 1 hour, or another bounded duration.

**Scope**

Add an `execution` object to the planned task contract with `duration_seconds`, ramp fields, stop policy, grace period, worker timeout, iteration limit, and data policy.

**Acceptance Criteria**

- Contract docs define all execution fields.
- API validation rules reject unbounded execution unless explicitly allowed.
- k6 and JMeter mapping decisions are documented before runtime changes.
- Dashboard read model can show duration and stop policy fields.

**Non-goals**

- Do not implement distributed shards in this issue.
- Do not add new target apps.

**Dependencies**

- `docs/v3/specs/task-execution-model.md`.

## Issue 9: Add Graceful Stop And Worker Timeout Policy

**Title**

Add graceful stop and worker timeout policy

**Labels**

- `area:worker`
- `area:reliability`
- `type:implementation`

**Problem**

Duration-based execution needs a predictable stop sequence so workers stop new traffic at the requested boundary and still protect the host from runaway engine processes.

**Scope**

Implement stop metadata, graceful stop handling, force-stop fallback, and worker-level timeout calculation for supported engines.

**Acceptance Criteria**

- `graceful_stop` is the default stop policy.
- A 1-hour task stops new traffic at 1 hour and waits only for the configured grace period.
- Forced stops are recorded in result metadata.
- Worker tests cover timeout and forced-stop paths.

**Non-goals**

- Do not add histogram-based distributed aggregation.
- Do not change target app behavior.

**Dependencies**

- Duration-based task execution model.

## Issue 10: Add Distributed Task Shard Model

**Title**

Add distributed task shard model

**Labels**

- `area:scheduler`
- `area:worker`
- `type:architecture`

**Problem**

The current runtime assigns one task to one worker and stores one result. Multi-agent execution needs logical task, task run, shard, claim, and result shard concepts.

**Scope**

Define and implement task run and shard lifecycle, agent selectors, agent labels, engine capability matching, target network reachability, and partial success status.

**Acceptance Criteria**

- A logical task can create multiple shard sub-runs.
- Each shard can declare an agent selector.
- Workers claim eligible shards instead of requiring Control Plane push dispatch.
- Partial success is represented distinctly from full success and full failure.

**Non-goals**

- Do not implement advanced capacity scoring.
- Do not require target apps to connect to the Control Plane.

**Dependencies**

- `docs/v3/specs/distributed-agent-execution.md`.
- Scoped access design for worker claim and result submission.

## Issue 11: Add Dataset Partitioning For Multi-Agent Execution

**Title**

Add dataset partitioning for multi-agent execution

**Labels**

- `area:api`
- `area:dataset`
- `type:contract`

**Problem**

Operators need to split datasets, such as 5000 rows into 2000 and 3000 row shards, and assign those shards to different agents.

**Scope**

Add dataset source, format, partition strategy, shard range, and per-shard assignment contracts. Start with `manual_ranges`, `range`, and `manual`.

**Acceptance Criteria**

- API contract accepts dataset shard metadata.
- Manual offset/limit ranges can represent 2000/3000 splits.
- Validation detects missing shard ids and overlapping ranges where overlap is not allowed.
- Workers receive only the dataset shard assigned to the claimed shard.

**Non-goals**

- Do not implement `hash`, `weighted`, or `round_robin` in MVP.
- Do not add external dataset storage in this issue unless required by an accepted artifact design.

**Dependencies**

- Distributed task shard model.
- Artifact reference policy.

## Issue 12: Add Distributed Result Aggregation Model

**Title**

Add distributed result aggregation model

**Labels**

- `area:results`
- `area:api`
- `type:contract`

**Problem**

Distributed runs produce per-agent summaries that cannot be naively averaged into correct global latency percentiles.

**Scope**

Define result shard storage, aggregate summary rules, aggregation quality metadata, and conservative global summaries.

**Acceptance Criteria**

- Total requests and failed requests are summed.
- Error rate is recalculated from summed totals.
- Throughput is recalculated across the run window.
- p95 and p99 are not averaged across shards.
- API marks global percentiles unavailable unless mergeable data exists.

**Non-goals**

- Do not implement histogram-based merge in MVP.
- Do not require inline raw reports for large runs.

**Dependencies**

- Distributed task shard model.
- Future artifact collection policy.

## Issue 13: Add Dashboard Controls For Execution Duration And Distribution

**Title**

Add dashboard controls for execution duration and distribution

**Labels**

- `area:dashboard`
- `area:api`
- `type:feature`

**Problem**

Operators need task creation controls for duration, graceful stop, dataset partitioning, and agent selection once the API can enforce them.

**Scope**

Add Create Task Wizard controls for execution duration, stop policy, grace period, single-agent versus sharded mode, agent selectors, dataset partitioning, and shard review.

**Acceptance Criteria**

- Dashboard defaults to `graceful_stop`.
- 10-minute and 1-hour presets are available.
- Dataset shards are visible before submission.
- Task detail shows per-shard status and aggregation quality.

**Non-goals**

- Do not expose controls before backend support is available.
- Do not build a general agent administration console in this issue.

**Dependencies**

- External API v1 execution and distribution objects.
- Distributed result aggregation model.

## Issue 14: Add API Contract Tests For Execution And Distribution Objects

**Title**

Add API contract tests for execution and distribution objects

**Labels**

- `area:api`
- `area:tests`
- `type:quality`

**Problem**

Future dashboard and automation clients need stable validation behavior for execution, distribution, dataset, shard, and aggregation objects.

**Scope**

Add contract tests for valid and invalid task creation payloads, single-agent duration tasks, sharded dataset tasks, agent selector labels, and aggregation response shape.

**Acceptance Criteria**

- Tests cover single-agent 10-minute task creation.
- Tests cover single-agent 1-hour graceful stop creation.
- Tests cover multi-agent 2000/3000 dataset split payloads.
- Tests cover different target network labels.
- Tests cover invalid stop policy, missing shard id, and overlapping dataset ranges.

**Non-goals**

- Do not test real multi-host execution in unit tests.
- Do not require Docker target-app smoke for every contract test.

**Dependencies**

- External API v1 implementation plan.
- Task execution model.
- Distributed agent execution model.
