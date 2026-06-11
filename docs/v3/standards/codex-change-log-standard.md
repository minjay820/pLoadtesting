# Codex Change Log Standard

## Purpose

Daily change logs provide a same-day record of substantive Codex changes.

They are not a replacement for git history. They explain why documentation, behavior, configuration, or governance changed and where to look next.

## Location

Daily logs live at:

```text
docs/v3/changes/daily/YYYY-MM-DD.md
```

Use the repository's current local date for the filename.

## Required Timing

Add or update the daily log in the same session as any substantive Codex change.

If a task starts as analysis-only and later changes tracked files, create or update the daily log before finishing.

## Required Content

Each daily log should include:

- date
- scope
- changed files or documentation areas
- summary of what changed
- validation performed
- follow-ups or unresolved migration work
- commit hash, if a commit was created

## Non-Substantive Sessions

No daily log is required for pure questions, pure review, analysis-only work, typo-only edits, or sessions with no tracked file change unless the user asks for a record.

## Commit Hash Updates

If a commit is created after the daily log is written, the final response must report the commit hash. The daily log may use `Pending until commit is created` for the commit that contains the daily log itself, because recording that exact hash inside the same commit would require an unnecessary amend loop.
