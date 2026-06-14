# Codex Repository Instructions

This repository uses `docs/v3/` as the active documentation trunk for Codex-governed work.

## Required Startup Flow

Before making any substantive change, every Codex session must:

1. Read `docs/v3/README.md`.
2. Follow only the directly relevant indexes and links for the current task.
3. Avoid recursive or blanket reading of all `docs/v3/` content unless the user explicitly asks for a full audit.
4. Check the current-day daily change log path: `docs/v3/changes/daily/YYYY-MM-DD.md`.

## Substantive Change Rule

Any substantive Codex change must update the relevant `docs/v3/` documentation in the same session.

Substantive changes include:

- Code logic, data model, API behavior, or UI behavior changes.
- Runtime scripts, startup settings, deployment settings, environment variables, Docker, CI/CD, or tracked execution configuration changes.
- Documentation governance, documentation structure, indexes, ADRs, runbooks, specs, or domain documents being added or changed.
- Legacy documentation being mirrored, classified, normalized, or reorganized.
- Test strategy, validation flow, operating procedure, or system behavior documentation changes.

The following are not necessarily substantive changes:

- Pure questions, inventory, or review work without repo modification.
- Typo or formatting-only edits that do not change meaning.
- User requests that explicitly say analysis-only, no modification, or no commit.
- Sessions with no tracked file changes.

## Documentation Update Requirements

For every substantive change:

1. Update the directly relevant `docs/v3/` document.
2. Add, supplement, or update `docs/v3/changes/daily/YYYY-MM-DD.md`.
3. Ensure every new or changed document is reachable from `docs/v3/README.md` or a child README index.
4. If governance rules change, update all of these together:
   - `AGENTS.md`
   - `docs/v3/README.md`
   - `docs/v3/standards/*`
   - the current daily change log

## Legacy Documentation Migration

During documentation migration:

1. Do not directly delete or rewrite legacy documentation.
2. Mirror legacy content into `docs/v3/legacy/` first.
3. Normalize mirrored content into the correct active area after mirroring:
   - `docs/v3/domains/`
   - `docs/v3/specs/`
   - `docs/v3/adr/`
   - `docs/v3/runbooks/`
4. Maintain a leaf normalization map when legacy material is mirrored. The map must include:
   - legacy source path
   - mirrored path
   - normalized target path
   - migration status
   - notes or decision rationale

## Commit Rule

If the session includes any of the following, create a git commit before finishing unless the user explicitly says not to commit:

- Code changes
- Runtime script changes
- API behavior changes
- UI behavior changes
- Tracked execution configuration changes
- Documentation governance rule changes

Commit exceptions:

- The user explicitly asks not to commit.
- There are no tracked file changes.
- Tests or validation fail and user judgment is needed.
- The environment cannot run `git commit`.
- The task is analysis, inventory, reading, or advice only with no repo modification.

Commit messages should concisely describe the governance or documentation change.

## Repository Context

For this repository, common documentation entry points include:

- Root overview: `README.md`
- Contributor workflow: `CONTRIBUTING.md`
- Public roadmap: `ROADMAP.md`
- Security policy: `SECURITY.md`
- Third-party notices: `THIRD_PARTY_NOTICES.md`
- Active Codex documentation trunk: `docs/v3/README.md`
- Existing legacy docs pending migration: `docs/`, `control-plane/ARCHITECTURE.md`, engine READMEs, and root project docs
- Runtime stack: Docker Compose, Django/DRF control plane, FastAPI target app, FastAPI worker agent, Redis/Celery, k6, JMeter, InfluxDB, and Grafana

## Public Project Document Updates

When updating root-level public project documents, keep them aligned with `docs/v3/` rather than treating them as separate sources of truth.

- `README.md` should remain a concise public orientation and link into active `docs/v3/` material for deeper operational detail.
- `ROADMAP.md` should summarize current horizons and point to issue-sized roadmap drafts under `docs/v3/roadmap/`.
- `SECURITY.md` should state the current preview security boundary accurately and avoid implying production-grade access controls before they are implemented.
- `CONTRIBUTING.md` should reference the current validation commands and docs/v3 update expectations.
- `THIRD_PARTY_NOTICES.md` should be updated when new committed integrations, runtime dependencies, or redistributed assets materially affect notice obligations.
