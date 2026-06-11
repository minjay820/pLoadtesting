# Codex Docs Update Standard

## Session Entry

At the start of any substantive Codex task:

1. Read `docs/v3/README.md`.
2. Identify the smallest relevant documentation area.
3. Read only the linked docs needed for the task.
4. Note the current daily log path.

## During Work

When a repo change becomes substantive, update documentation before finishing the session.

Documentation should be:

- specific enough to help future maintainers
- linked from the relevant README index
- consistent with existing terminology
- clear about whether it describes implemented behavior, planned behavior, or migration status

Do not present planned behavior as implemented behavior.

## New Documents

When adding a new document:

1. Put it under the correct `docs/v3/` area.
2. Add it to the nearest README index.
3. Add or update the daily change log.
4. If it comes from legacy material, mirror first and update `docs/v3/legacy/leaf-normalization-map.md`.

## Existing Documents

When updating an existing document:

1. Preserve useful existing content.
2. Make the smallest semantic update that reflects the repo change.
3. Update index text if the document scope changes.
4. Update the daily change log.

## Governance Changes

Governance changes must update the complete governance set in one session:

- `AGENTS.md`
- `docs/v3/README.md`
- every file under `docs/v3/standards/`
- the current daily change log

This prevents future Codex sessions from receiving conflicting documentation rules.
