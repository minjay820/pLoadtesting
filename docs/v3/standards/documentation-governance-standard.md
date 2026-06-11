# Documentation Governance Standard

## Purpose

This standard defines how Codex sessions keep repository documentation current, traceable, and safe to migrate.

The rules are project-agnostic. Repository-specific examples may appear in indexes, runbooks, daily logs, or migration maps.

## Active Trunk

`docs/v3/` is the active documentation trunk.

Before making a substantive change, Codex must read `docs/v3/README.md` and then open only the directly relevant child indexes or linked documents for the task.

## Required Same-Session Updates

Any substantive change must update documentation in the same session. At minimum, update:

- the directly relevant active document under `docs/v3/`
- the current daily change log under `docs/v3/changes/daily/YYYY-MM-DD.md`
- the nearest README index when a document is added, moved, or renamed

If the change modifies governance itself, update all governance surfaces together:

- `AGENTS.md`
- `docs/v3/README.md`
- `docs/v3/standards/*`
- the current daily change log

## Traceability

Every active `docs/v3/` document must be reachable from `docs/v3/README.md` or a child README index.

Do not create orphan documents. If a new document is useful enough to keep, add it to the relevant index in the same session.

## Legacy Safety

Do not directly delete or rewrite legacy documents during migration.

The required sequence is:

1. Mirror legacy content into `docs/v3/legacy/`.
2. Record the source, mirror, target, status, and rationale in the leaf normalization map.
3. Normalize content into the correct active area.
4. Keep the original legacy file until the user explicitly approves removal or archival.

## Validation

Before finishing, check:

- `AGENTS.md` points future Codex sessions to `docs/v3/`.
- `docs/v3/README.md` indexes every new or changed documentation area.
- Standards describe update timing and daily log requirements.
- The daily log records the session.
- Legacy migration rules avoid deletion of old files.
- Commit requirements have been followed or the exception is stated.
