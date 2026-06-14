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

## Issue 7: Decide Whether To Backfill Generic Payload Shortcut Parity

**Summary**

Decide whether `payload-jmeter-download` should remain a documented generic shortcut or receive an exact k6 peer.

**Problem / Use Case**

The target profile coverage matrix has one strict non-parity profile by design.

**Proposed Solution**

Keep the current gap documented unless the team wants every retained convenience profile to have exact k6/JMeter symmetry.

**Expected Behavior**

The coverage matrix remains explicit and auditable.

**Acceptance Criteria**

- Decision is recorded in the target profile coverage doc or an ADR.
- If backfilled, the new profile has reciprocal `equivalent_profile_id` metadata and tests.
- If retained, the current low-priority gap remains documented.

**Validation**

- `target-apps/tests/test_suite.py` parity validation passes.

**Dependencies**

- Existing target profile coverage matrix.
