# Artifact Lifecycle

This spec defines the current Phase 7 artifact lifecycle contract for Core preview APIs. It hardens artifact metadata, result reporting provenance, retention expectations, and future-safe download behavior without adding a durable artifact store, report center, database migration, or unsafe filesystem download.

## Current Runtime Boundary

The current runtime has no persisted artifact table and no artifact object storage. Artifact metadata is derived at read time from:

- worker-generated local output conventions
- worker-captured process streams stored in `TestResult.raw_report`
- Control Plane task and result metadata

Worker-local temporary files are implementation detail only. They are not a public API contract and must not be exposed as local filesystem paths.

## Artifact Sources

Current artifact source categories:

- `worker_output`: files the worker may generate during execution, such as k6 JSON output or JMeter JTL/log files
- `result_raw_report`: persisted `stdout`, `stderr`, or structured engine output already stored in `TestResult.raw_report`
- `engine_convention`: planned artifact rows derived from the engine contract even when no persisted evidence exists yet
- `external_reference`: reserved for future signed URL or external object storage references

## Artifact Root Convention

Current worker execution uses local temporary paths for engine output, for example worker-local files under `/tmp`. These paths are not durable lifecycle identifiers and are not part of the public API.

Public artifact metadata must use stable task-scoped identifiers such as:

- `k6-summary-json`
- `k6-stdout`
- `jmeter-jtl`

The contract must never expose worker-local path strings, raw path traversal inputs, or direct filesystem roots.

## Task Artifact Relation

Artifacts are task-scoped metadata entries. A task can return planned artifact rows even when no persisted artifact record exists yet.

Current relation rules:

- artifact rows are derived from `LoadTestTask.engine`
- artifact evidence can be upgraded by `TestResult.raw_report`
- a task can expose `planned` rows before execution finishes
- a completed task can still show `missing` rows when the engine convention implies an output but Core has no persisted evidence for it

## Engine Artifact Kinds

Artifact kinds in this phase are:

- `summary_json`
- `html_report`
- `jtl`
- `raw_log`
- `stdout`
- `stderr`
- `engine_output`
- `unknown`

Current engine conventions:

| Engine | Current artifact rows |
|---|---|
| `k6` | `summary_json`, `stdout`, `stderr`, `engine_output`, `html_report` |
| `jmeter` | `jtl`, `raw_log`, `stdout`, `stderr`, `engine_output`, `html_report` |
| other/unknown | `engine_output`, `unknown` fallback rows |

`html_report` is planning metadata only in this phase. It should remain `planned` unless future persisted evidence is added.

## Worker Output Convention

Current worker runtime conventions:

- k6 writes line-oriented JSON output to a worker-local file and posts parsed summary fields plus `raw_report`
- JMeter writes JTL and log files to worker-local paths and posts parsed summary fields plus `raw_report`
- both engines can persist `stdout` and `stderr` inside `TestResult.raw_report`

The Control Plane artifact contract does not assume those worker-local files are still present after callback completion.

## Metadata Creation Timing

Artifact metadata is derived at read time by `GET /api/tasks/{id}/artifacts/`.

Current timing rules:

- before result callback: return engine-based `planned` rows
- after result callback: upgrade rows to `available` only when persisted evidence exists
- after result callback with missing persisted evidence for an expected worker file: return `missing`

This phase does not create or update a persisted artifact manifest.

## Artifact States

Artifact states are:

- `planned`: expected by engine convention but no trustworthy persisted evidence exists yet
- `available`: artifact content or structured representation is already persisted in Control Plane metadata
- `missing`: the task has a result and the engine convention implies an output, but current persisted metadata does not prove availability
- `expired`: reserved for future cleanup and retention enforcement
- `external`: reserved for future managed external storage references

Current runtime primarily uses `planned`, `available`, and `missing`.

## Retention Policy

Current MVP retention policy:

- `LoadTestTask` and `TestResult` rows are the retained source of truth in Core
- worker-local output files are ephemeral and not guaranteed after execution
- `stdout`, `stderr`, and other `raw_report` entries are retained only if already stored in `TestResult.raw_report`
- artifact metadata should never claim durable availability for worker-local files without persisted evidence

This phase does not add TTL fields, background cleanup jobs, or artifact expiry transitions in storage.

## Cleanup Policy Future

Future cleanup policy may add:

- explicit retention windows by artifact kind
- background cleanup jobs
- lifecycle transitions from `available` to `expired`
- external object storage deletion policies

Any future cleanup policy must preserve stable metadata semantics and must not silently convert unavailable local paths into downloadable artifacts.

## Download Policy Future

Future download behavior should use a controlled route such as `GET /api/tasks/{id}/artifacts/{artifact_id}/download/`.

Current Phase 7 behavior:

- the route can return structured `501 not implemented`
- no real file is downloaded
- no worker-local path is exposed

Future implementation requirements:

- path-safe artifact lookup by task and artifact identifier only
- no arbitrary path input or path traversal
- no direct local filesystem path exposure
- support for controlled redirects, signed URLs, or external object storage only after an explicit storage contract exists

## Security Notes

- Do not expose worker-local temporary file paths.
- Do not trust client-provided artifact paths.
- Do not allow arbitrary path traversal or file reads.
- Do not assume `artifact://` dataset references imply downloadable task artifacts.
- Keep artifact metadata and download behavior neutral for external clients and downstream integrations.

## Result Metric Provenance

Result summaries can expose engine-reported percentile values for a single `TestResult`, but Core must not invent global percentiles.

Current provenance rules:

- `metrics_source` is `test_result` when values come from the stored result row
- `percentile_policy` is `engine_reported` for task-level persisted percentiles
- Core must not average shard `p95` or `p99`
- exact global percentile merge requires raw samples, histogram buckets, HDR histogram, t-digest, or another mergeable format

This phase does not implement advanced percentile merge.

## Non-Goals

- complete report generation
- artifact browser UI
- unsafe filesystem download
- object storage implementation
- signed URL implementation
- token system changes
- distributed scheduler redesign
- exact percentile merge
