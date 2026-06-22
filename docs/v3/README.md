# pLoadtesting Documentation v3

`docs/v3/` is the active documentation trunk for Codex-governed work in this repository.

Before any substantive change, read this file first, then follow only the directly relevant child indexes and links for the task. Do not recursively read the full documentation tree unless the task requires a full audit.

## Governance

- Repo-level Codex instructions: [AGENTS.md](../../AGENTS.md)
- Documentation governance standard: [standards/documentation-governance-standard.md](standards/documentation-governance-standard.md)
- Documentation update matrix: [standards/documentation-update-matrix.md](standards/documentation-update-matrix.md)
- Codex docs update standard: [standards/codex-docs-update-standard.md](standards/codex-docs-update-standard.md)
- Codex change log standard: [standards/codex-change-log-standard.md](standards/codex-change-log-standard.md)
- Daily change log template: [templates/codex-daily-change-log-template.md](templates/codex-daily-change-log-template.md)
- Today's daily change log: [changes/daily/2026-06-23.md](changes/daily/2026-06-23.md)

## Active Documentation Areas

- Domain documents: [domains/README.md](domains/README.md)
- Specifications: [specs/README.md](specs/README.md)
- Architecture decision records: [adr/README.md](adr/README.md)
- Runbooks: [runbooks/README.md](runbooks/README.md)
- Roadmap drafts: [roadmap/README.md](roadmap/README.md)
- Legacy migration staging: [legacy/README.md](legacy/README.md)
- Legacy leaf normalization map: [legacy/leaf-normalization-map.md](legacy/leaf-normalization-map.md)

## Repository-Specific Orientation

This project is a multi-engine load testing ecosystem:

- `target-app/`: FastAPI reference target service.
- `target-apps/`: diversified local target app suite for controlled scenario coverage.
- `control-plane/`: Django 5, Django REST Framework, Celery, Redis, and SQLite MVP orchestration layer.
- `workers/`: FastAPI worker agent for k6 and JMeter execution.
- `engines/k6/`: k6 JavaScript load test scripts.
- `engines/jmeter/`: JMeter `.jmx` plans and report assets.
- `docs/v3/domains/p-loadtesting-target-profile-coverage.md`: authoritative profile-level k6/JMeter parity matrix.
- `docs/v3/domains/p-loadtesting-core-boundary.md`: Core responsibility boundary for external clients and downstream integrations.
- `GET /api/tasks/templates/coverage/`: machine-readable profile coverage export for dashboard and API consumers.
- `GET /api/tasks/`, `GET /api/tasks/{id}/`, `GET /api/tasks/{id}/result-summary/`, and `GET /api/tasks/{id}/artifacts/`: preview read contracts for run history, detail, result summary, and artifact metadata.
- `docs/v3/domains/p-loadtesting-phase-completion.md`: current Phase 0-4 completion assessment.
- `docs/v3/domains/p-loadtesting-web-dashboard.md`: future dashboard MVP plan.
- `docs/v3/specs/dashboard-read-model.md`: future dashboard read model over current preview APIs.
- `docs/v3/specs/api-consumer-guide.md`: preview API consumer guide for templates, coverage, and task creation.
- `docs/v3/specs/external-api-v1.md`: future stable external API contract plan.
- `docs/v3/specs/external-client-contract.md`: current Core contract for external clients, downstream integrations, and compatible dashboards.
- `docs/v3/specs/api-versioning-policy.md`: preview, stable candidate, experimental, and planning-only API compatibility policy.
- `docs/v3/specs/repository-publication-policy.md`: planned GitLab-private and GitHub-public publication policy.
- `docs/v3/specs/task-execution-model.md`: duration, stop policy, worker timeout, and shard metadata contract.
- `docs/v3/specs/distributed-agent-execution.md`: manual shard distribution metadata, dataset partition, and aggregation contract.
- `docs/v3/specs/artifact-lifecycle.md`: artifact metadata lifecycle, retention, download placeholder, and result provenance contract.
- `docs/v3/specs/api-token-auth.md`: future scoped API access plan.
- `docs/v3/runbooks/distributed-deployment.md`: cross-host deployment planning runbook.
- `docs/v3/runbooks/external-db-runtime.md`: PostgreSQL runtime settings and external database validation runbook.
- `docs/v3/runbooks/local-smoke-image-build.md`: local smoke image build and inspect flow for deployment validation.
- `docs/v3/roadmap/github-issues-dashboard-api-deployment.md`: issue-sized roadmap drafts for dashboard, API, access, and deployment work.
- `docker-compose.yml`: local ecosystem orchestration for target app, control plane, worker, Redis, InfluxDB, and Grafana.
- `.github/workflows/ci.yml`: CI workflow.

Existing pre-v3 documentation remains in place until it is mirrored into `docs/v3/legacy/` and normalized into the active documentation areas. Do not delete or rewrite legacy documents as part of migration unless the user explicitly requests a cleanup after migration is complete.

## Daily Change Logs

Every substantive Codex change must add, supplement, or update the matching daily file:

```text
docs/v3/changes/daily/YYYY-MM-DD.md
```

Use [templates/codex-daily-change-log-template.md](templates/codex-daily-change-log-template.md) for new daily files.

## What Counts As Substantive

Substantive changes include code behavior, data models, APIs, UI behavior, runtime scripts, deployment configuration, Docker, CI/CD, tracked execution configuration, documentation governance, documentation structure, ADRs, runbooks, specs, domain docs, legacy migration, test strategy, validation flow, operating procedure, or system behavior documentation changes.

Typo-only edits, formatting-only edits, pure review, pure inventory, or analysis-only work are not necessarily substantive when they do not modify tracked files or change meaning.

## Root Public Documents

Root-level public project documents are concise entry points and should stay aligned with the active docs trunk:

- `README.md`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `ROADMAP.md`
- `SECURITY.md`
- `THIRD_PARTY_NOTICES.md`
- `LICENSE`

When these files describe implemented behavior, planned behavior, validation, security posture, or third-party obligations, prefer linking to the relevant `docs/v3/` source of truth instead of duplicating long operational detail.
