# Artifact Lifecycle

This spec defines the current Phase 10 artifact lifecycle contract for Core preview APIs. It hardens artifact metadata, manifest versioning, worker registration payload compatibility, and size/checksum enrichment without adding a complete report center, object storage, or unsafe filesystem download.

## Current Runtime Boundary

The current runtime now has a persisted artifact manifest MVP but still has no durable artifact object storage. Artifact metadata can come from:

- persisted `TaskArtifact` manifest rows
- worker-generated local output conventions
- worker-captured process streams stored in `TestResult.raw_report`
- Control Plane task and result metadata

Worker-local temporary files are implementation detail only. They are not a public API contract and must not be exposed as local filesystem paths.

## Artifact Sources

Current artifact source categories:

- `artifact_manifest`: persisted manifest metadata stored in the Control Plane database
- `worker_output`: files the worker may generate during execution, such as k6 JSON output or JMeter JTL/log files
- `worker_registration`: safe manifest entries posted by the worker through the result callback payload
- `result_raw_report`: persisted `stdout`, `stderr`, or structured engine output already stored in `TestResult.raw_report`
- `engine_convention`: planned artifact rows derived from the engine contract even when no persisted evidence exists yet
- `external_reference`: reserved for future signed URL or external object storage references

## Artifact Root Convention

Current worker execution uses local temporary paths for engine output, for example worker-local files under `/tmp`. These paths are not durable lifecycle identifiers and are not part of the public API.

Public artifact metadata must use stable task-scoped identifiers and controlled object references such as:

- `k6-summary-json`
- `k6-stdout`
- `jmeter-jtl`
- `artifact://tasks/<task-id>/<artifact-id>`
- `object://artifacts/<logical-key>`
- `external://storage/<logical-key>`

The contract must never expose worker-local path strings, raw path traversal inputs, or direct filesystem roots.

## Task Artifact Relation

Artifacts are task-scoped metadata entries. A task can return planned artifact rows even when no persisted artifact record exists yet.

Current relation rules:

- artifact rows are derived from `LoadTestTask.engine`
- persisted manifest rows are stored per task and artifact identifier
- artifact evidence can be upgraded by `TestResult.raw_report`
- a task can expose `planned` rows before execution finishes
- a completed task can still show `missing` rows when the engine convention implies an output but Core has no persisted evidence for it
- when a persisted manifest row and a derived row share the same `artifact_id`, the persisted manifest row wins

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
- workers can now post an optional `artifact_manifest` alongside `POST /api/tasks/{id}/results/`
- worker artifact registration is task-scoped and uses controlled logical object references only
- worker artifact registration must not send worker-local absolute paths, `file:///...`, or traversal strings

The Control Plane artifact contract does not assume those worker-local files are still present after callback completion.

## Metadata Creation Timing

Artifact metadata is returned by `GET /api/tasks/{id}/artifacts/` from a merge of persisted and derived sources.

Current timing rules:

- before result callback: return engine-based `planned` rows
- after worker manifest registration: return persisted rows immediately
- after result callback: upgrade rows to `available` only when persisted evidence exists
- after result callback with missing persisted evidence for an expected worker file: return `missing`
- when persisted and derived metadata overlap on the same `artifact_id`, the persisted row overrides the derived row

Phase 8 adds a persisted artifact manifest MVP through `TaskArtifact`. Phase 9 adds narrow worker registration through the existing result callback path.

## Artifact States

Artifact states are:

- `planned`: expected by engine convention but no trustworthy persisted evidence exists yet
- `available`: artifact content or structured representation is already persisted in Control Plane metadata
- `missing`: the task has a result and the engine convention implies an output, but current persisted metadata does not prove availability
- `expired`: reserved for future cleanup and retention enforcement
- `external`: reserved for future managed external storage references

Current runtime primarily uses `planned`, `available`, `missing`, `expired`, and `external`.

## Persisted Artifact Manifest MVP

Phase 8 adds a minimal persisted manifest model with task-scoped rows. The manifest stores safe metadata only:

- task
- artifact identifier
- kind
- state
- name
- content type
- size
- controlled object reference
- optional checksum
- optional expiry metadata
- provenance
- safe metadata JSON

The manifest does not expose worker-local paths and does not imply a real download implementation.

## Manifest Versioning

Current artifact manifest contract version:

- `artifact_manifest_version = "1.0"`

Current versioning rules:

- worker registration payloads should send `artifact_manifest_version: "1.0"`
- the public `GET /api/tasks/{id}/artifacts/` response exposes the current contract version in `contract.artifact_manifest_version`
- legacy list-only worker payloads remain accepted for backward compatibility and are treated as `unspecified` legacy payloads
- future unsupported manifest versions are currently rejected rather than downgraded silently

## Worker Artifact Registration MVP

Phase 9 allows the worker to send known artifact manifest entries together with `POST /api/tasks/{id}/results/`.

Current registration rules:

- the worker builds deterministic artifact ids by engine convention
- the worker sends a versioned payload envelope with `artifact_manifest_version` and `items`
- the worker registers only safe metadata and logical object references
- the Control Plane validates kind, state, object reference, and safe metadata before upsert
- the Control Plane validates `checksum_sha256` format when present
- invalid local paths, traversal strings, and sensitive metadata are rejected
- registration remains additive to existing result callback behavior and does not require the worker to import Django models

Current accepted payload formats:

- preferred:

```json
{
  "artifact_manifest_version": "1.0",
  "items": [
    {
      "artifact_id": "k6-stdout",
      "kind": "stdout",
      "state": "available"
    }
  ]
}
```

- backward-compatible legacy:

```json
[
  {
    "artifact_id": "k6-stdout",
    "kind": "stdout",
    "state": "available"
  }
]
```

Current engine mapping:

| Engine | Registered artifact ids | `available` evidence |
|---|---|---|
| `k6` | `k6-summary-json`, `k6-stdout`, `k6-stderr`, `k6-engine-output` | summary output evidence, captured `stdout`, captured `stderr`, or persisted `raw_report` |
| `jmeter` | `jmeter-jtl`, `jmeter-html-report`, `jmeter-stdout`, `jmeter-stderr`, `jmeter-engine-output` | JTL evidence, HTML report evidence, captured `stdout`, captured `stderr`, or persisted `raw_report` |
| unknown | `engine-output` | persisted `raw_report` evidence only |

`available` must depend on evidence. Worker registration must not invent file existence just because a worker-local output path was expected.

## Size And Checksum Enrichment

Phase 10 adds safe enrichment for `size_bytes` and `checksum_sha256`.

Current enrichment rules:

- `stdout` and `stderr` can derive size and SHA-256 from captured string or bytes evidence
- `engine_output` can derive size and SHA-256 from a stable serialized `raw_report`
- summary or report artifact rows without safe in-memory evidence remain `available` or `planned` based on evidence, but can keep `size_bytes` and `checksum_sha256` empty
- raw artifact content is not copied into artifact metadata
- worker registration does not read arbitrary local files to compute size or checksum

## Object Reference Rules

Current allowed object reference shapes:

- `artifact://tasks/<task-id>/<artifact-id>`
- `object://...`
- `external://...`
- `null`

Current rejected object reference shapes:

- `/absolute/local/path`
- `../relative/path`
- `./relative/path`
- `file:///...`

Validation rules:

- absolute local paths are rejected
- path traversal segments are rejected
- `artifact://tasks/...` references must match the owning task and artifact identifier
- object references are logical identifiers only, not filesystem paths
- `checksum_sha256` must be a 64-character lowercase hex SHA-256 value when provided

Phase 9 worker registration uses `artifact://tasks/<task-id>/<artifact-id>` for current logical references. Future `object://...` and `external://...` references remain valid for later storage backends, but the worker does not expose local paths in this phase.

## Retention Policy

Current MVP retention policy:

- `LoadTestTask` and `TestResult` rows are the retained source of truth in Core
- `TaskArtifact` rows are the retained source of truth for persisted artifact manifest metadata
- worker-local output files are ephemeral and not guaranteed after execution
- `stdout`, `stderr`, and other `raw_report` entries are retained only if already stored in `TestResult.raw_report`
- artifact metadata should never claim durable availability for worker-local files without persisted evidence
- `expires_at` can carry retention metadata even before cleanup jobs exist

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
- it returns `404` when the requested artifact identifier does not exist for the task
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
- Do not store secrets, tokens, credentials, cookies, sessions, authorization values, or api keys in manifest metadata.
- Keep artifact metadata and download behavior neutral for external clients and downstream integrations.

## Result Metric Provenance

Result summaries can expose engine-reported percentile values for a single `TestResult`, but Core must not invent global percentiles.

Current provenance rules:

- `metrics_source` is `test_result` when values come from the stored result row
- `percentile_policy` is `engine_reported` for task-level persisted percentiles
- Core must not average shard `p95` or `p99`
- exact global percentile merge requires raw samples, histogram buckets, HDR histogram, t-digest, or another mergeable format

This phase does not implement advanced percentile merge.

## External Client Handling

External clients should:

- treat persisted manifest rows as the authoritative metadata when present
- treat derived rows as safe fallback metadata when persisted rows do not exist yet
- tolerate additive manifest fields in future phases
- treat `download_available=false` as the current durable behavior even for `available` manifest rows
- handle `planned`, `missing`, `expired`, and `external` distinctly rather than collapsing them into one unavailable state

## Non-Goals

- complete report generation
- artifact browser UI
- unsafe filesystem download
- object storage implementation
- signed URL implementation
- token system changes
- distributed scheduler redesign
- exact percentile merge
