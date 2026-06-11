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
- Today's daily change log: [changes/daily/2026-06-11.md](changes/daily/2026-06-11.md)

## Active Documentation Areas

- Domain documents: [domains/README.md](domains/README.md)
- Specifications: [specs/README.md](specs/README.md)
- Architecture decision records: [adr/README.md](adr/README.md)
- Runbooks: [runbooks/README.md](runbooks/README.md)
- Legacy migration staging: [legacy/README.md](legacy/README.md)
- Legacy leaf normalization map: [legacy/leaf-normalization-map.md](legacy/leaf-normalization-map.md)

## Repository-Specific Orientation

This project is a multi-engine load testing ecosystem:

- `target-app/`: FastAPI reference target service.
- `control-plane/`: Django 5, Django REST Framework, Celery, Redis, and SQLite MVP orchestration layer.
- `workers/`: FastAPI worker agent for k6 and JMeter execution.
- `engines/k6/`: k6 JavaScript load test scripts.
- `engines/jmeter/`: JMeter `.jmx` plans and report assets.
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
