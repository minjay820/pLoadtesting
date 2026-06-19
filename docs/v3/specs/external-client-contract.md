# External Client Contract

This document defines the Core contract for external clients, downstream integrations, compatible dashboards, and operational clients. It is a documentation contract only; it does not add new runtime behavior.

## Contract Purpose

The Core project exposes load testing capabilities through documented HTTP APIs, JSON payloads, and published schemas. External clients should integrate through those public surfaces rather than importing internal Python functions, reading private implementation files, or depending on storage details.

Core must remain independent from any specific external client implementation. Any capability requested by a downstream integration must be described as a generic Core capability that can be used by multiple API consumers.

## Integration Principles

- External clients use HTTP APIs, JSON payloads, and documented schemas.
- External clients should not depend on internal Python functions unless a package is explicitly documented as a stable public package.
- External clients should treat preview `/api/` routes as compatibility candidates, not final versioned contracts.
- Core should not reference or depend on a specific external client, dashboard, or integration layer.
- Core changes should be additive where possible and should preserve existing documented fields unless a deprecation path is documented.
- Client-specific needs should be translated into neutral Core concepts such as task templates, execution metadata, distribution metadata, shard plans, results, artifacts, or coverage metadata.

## Template Registry Contract

`GET /api/tasks/templates/` is the primary catalog for task creation. External clients should prefer template-driven task creation over direct script-path entry when a matching target profile exists.

The catalog is a registry/static read model. It does not depend on task rows, result rows, or external database seed data. A source checkout reads the target manifests and task templates from `target-apps/`; the control-plane image can fall back to bundled safe demo profile definitions under `apps/tasks/catalog/` when the repo-root catalog is outside the image build context.

Template rows currently expose:

- `target_app_id`
- `target_profile_id`
- `display_name`
- `description`
- `engine`
- `script_path`
- `target_url`
- `equivalent_profile_id`
- `workload_types`
- `safe_limits`
- `coverage_status`
- `coverage_group`
- `coverage_gap`
- `execution` when a profile defines a duration default

Template metadata is a stable candidate contract. New optional fields can be added without breaking compatible clients. Clients should ignore unknown fields.

Safe demo profiles are local-only, bounded-duration catalog profiles intended for deployment smoke. They use local target URLs, require no real credentials, and should be selected only for short validation runs. Compatible external clients must not use catalog discovery to start long tests or tests against third-party targets.

## Coverage Metadata Contract

`GET /api/tasks/templates/coverage/` is the machine-readable coverage export for catalog summaries, coverage matrices, and compatibility checks.

Current expected preview totals are:

```json
{
  "target_app_count": 10,
  "profile_count": 44,
  "k6_profile_count": 22,
  "jmeter_profile_count": 22,
  "exact_coverage_profile_count": 44,
  "gap_profile_count": 0
}
```

Coverage metadata is a stable candidate contract. Summary counts, target rows, profile rows, and gap rows should remain additive. Clients should not infer unsupported runtime behavior from coverage parity alone.

## Catalog Access Policy

`GET /api/tasks/templates/` and `GET /api/tasks/templates/coverage/` are read-only catalog APIs for compatible external clients. These endpoints can be read without the shared API access header because they expose static template and coverage metadata, not task records, result records, or worker state.

Task history, task detail, task creation, worker callbacks, result summaries, shard plans, and artifact metadata remain protected preview APIs. External clients should treat catalog access as separate from task runtime access.

## Task Creation Contract

External clients create tasks with `POST /api/tasks/`. The preferred request shape uses `target_app_id` and `target_profile_id`, then lets the Control Plane resolve engine, script path, target URL, default task parameters, execution defaults, and profile metadata.

Current task creation can include:

- `target_app_id`
- `target_profile_id`
- `created_by`
- `parameters`
- `scheduled_at`
- `execution`
- `distribution`

Manual task creation with direct `engine`, `script_path`, and `target_url` remains available for preview compatibility, but external clients should prefer templates when possible.

## Task History And Detail Read Contracts

`GET /api/tasks/` is the preview run history read contract. It returns `source`, `summary`, and `items` so external clients can show task history without depending on internal serializer shape.

The list supports `limit` with a bounded maximum and a simple `status` filter. Items expose safe fields only:

- `id`
- `status`
- `target_app_id`
- `target_profile_id`
- `engine`
- `created_at`
- `updated_at`

`GET /api/tasks/{id}/` is the preview task detail read contract. It returns `source`, `task`, `parameters`, `execution`, `distribution`, `result`, and `warnings`. `target_app_id` and `target_profile_id` are returned when the task was created from a template or when existing task metadata makes them available.

## Execution Object Contract

`execution` is an experimental runtime contract. The preview API validates it, normalizes it, and stores it in `LoadTestTask.parameters.execution`.

Supported fields:

- `duration_seconds`
- `ramp_up_seconds`
- `ramp_down_seconds`
- `stop_policy`
- `graceful_stop_seconds`
- `max_run_seconds`
- `iteration_limit`
- `data_policy`

Supported MVP values:

- `stop_policy`: `graceful_stop`, `hard_stop`
- `data_policy`: `duration_first`, `iteration_first`

Advanced stop policies and dataset-completion semantics remain future work. See [Task execution model](task-execution-model.md) for validation and engine mapping details.

## Distribution Object Contract

`distribution` is an experimental runtime contract. The preview API validates manual shard metadata, stores it in `LoadTestTask.parameters.distribution`, and generates `LoadTestTask.parameters.shard_execution_plan`.

Supported MVP fields:

- `mode=manual_shards`
- `result_merge_policy=summary_only`
- `shards[].shard_id`
- `shards[].agent_selector.labels`
- `shards[].dataset.source`
- `shards[].dataset.format`
- `shards[].dataset.offset`
- `shards[].dataset.limit`

Dataset sources must use `artifact://` or `inline://`. Dataset formats are `csv`, `jsonl`, and `json`. Full distributed scheduling, shard persistence, dataset loading, and exact percentile merge remain future work. See [Distributed agent execution](distributed-agent-execution.md).

## Shard Plan Contract

`GET /api/tasks/{id}/shard-plan/` is an experimental read-only preview endpoint. It returns the stored shard execution plan for tasks created with `distribution`.

The plan includes:

- `task_id`
- `distribution.mode`
- `distribution.result_merge_policy`
- `distribution.shard_count`
- `shards[]` entries with task, target, engine, agent selector, dataset, and execution metadata
- `result_aggregation` with the `summary_only` placeholder contract

External clients can use the shard plan to preview or export intended shard assignments. The current scheduler does not fan out shard rows to multiple workers.

## Result Summary Read Contract

`GET /api/tasks/{id}/result-summary/` is a preview result summary read contract. When a `TestResult` exists, Core maps stored summary fields into a response with `summary`, `latency`, `provenance`, additive `thresholds`, and `warnings`.

When no result exists, the endpoint returns `status=not_available`, null metric fields, a stable `provenance` object, and a `result_summary_not_available` warning. External clients should treat this as a normal waiting state, not as a task failure.

Request totals and failed request counts can be read directly from stored result summary fields. Average latency and percentile values are reported only from stored engine result data. Core does not calculate cross-shard exact percentiles in this phase.

Current provenance fields:

- `provenance.metrics_source`
- `provenance.engine`
- `provenance.percentile_policy`

Current latency fields are:

- `avg_ms`
- `p50_ms`
- `p95_ms`
- `p99_ms`

`p50_ms` remains `null` in the current runtime because the stored result model does not persist that percentile. Core must not synthesize missing percentiles.

Engine-reported percentiles are valid for a single stored result, but external clients must not average shard `p95` or `p99` values. Exact global percentile merge requires raw samples, histogram buckets, HDR histogram, t-digest, or equivalent mergeable structures.

## Artifact Metadata Read Contract

`GET /api/tasks/{id}/artifacts/` is an experimental preview read contract for artifact metadata. The current runtime returns a stable envelope with task-scoped artifact rows derived from engine conventions and persisted result evidence.

Current artifact item fields are:

- `artifact_id`
- `kind`
- `name`
- `state`
- `size_bytes`
- `checksum_sha256`
- `content_type`
- `created_at`
- `download_available`
- `download_url`
- `provenance.engine`
- `provenance.source`

Current artifact response envelope also includes:

- `contract.artifact_manifest_version`

Current artifact states are:

- `planned`
- `available`
- `missing`
- `expired`
- `external`

Current artifact kinds are:

- `summary_json`
- `html_report`
- `jtl`
- `raw_log`
- `stdout`
- `stderr`
- `engine_output`
- `unknown`

`stdout` and `stderr` become `available` only when those values are already persisted in `TestResult.raw_report` or when an equivalent persisted manifest row exists. `engine_output` becomes `available` only when a stored `raw_report` exists or a persisted manifest row proves availability. Engine-convention file rows such as `summary_json`, `jtl`, or `raw_log` remain `planned` before result callback and can become `missing` after result callback when Core has no persisted evidence for them.

`download_available` is always `false` in this phase and `download_url` is always `null`.

See [Artifact lifecycle](artifact-lifecycle.md) for retention, security notes, and non-goals.

Phase 8 adds a persisted artifact manifest MVP. External clients should treat persisted manifest rows as authoritative metadata when they exist, and treat derived rows as fallback metadata when they do not.

Current persisted manifest behavior:

- rows are upserted by `(task, artifact_id)`
- persisted rows can carry `expires_at`, checksum, storage backend, and controlled object reference metadata
- persisted rows must not expose local filesystem paths
- object references are logical identifiers only
- worker result callbacks can register persisted manifest rows through an optional `artifact_manifest` payload
- the Control Plane rejects invalid local paths, traversal strings, and sensitive manifest metadata
- `checksum_sha256` must be a valid 64-character lowercase hex SHA-256 string when present
- legacy list-only worker payloads remain accepted, while the preferred payload shape is a versioned envelope with `artifact_manifest_version: "1.0"`

Current object reference rules:

- allowed: `artifact://tasks/<task-id>/<artifact-id>`, `object://...`, `external://...`, or `null`
- rejected: absolute local paths, relative traversal, and `file:///...`

## Artifact Download Placeholder Contract

`GET /api/tasks/{id}/artifacts/{artifact_id}/download/` is a preview placeholder route. The current runtime can return structured `501 not implemented` metadata for a known artifact and structured `404` for an unknown artifact. It must not download a real file, expose a worker-local path, or accept arbitrary filesystem input.

Future download behavior must use controlled task and artifact identifiers only. Signed URLs or external object storage remain future work.

## Worker Artifact Registration Contract

Phase 9 adds a narrow worker artifact registration MVP through the existing result callback path. This is still an internal runtime boundary, but external clients that read artifact metadata should understand how persisted rows appear.

Current worker registration behavior:

- the worker can post `artifact_manifest` together with `POST /api/tasks/{id}/results/`
- the preferred payload shape is:
  - `artifact_manifest_version: "1.0"`
  - `items: [...]`
- persisted rows override derived rows with the same `artifact_id`
- current worker mappings are deterministic by engine:
  - k6: `k6-summary-json`, `k6-stdout`, `k6-stderr`, `k6-engine-output`
  - jmeter: `jmeter-jtl`, `jmeter-html-report`, `jmeter-stdout`, `jmeter-stderr`, `jmeter-engine-output`
  - unknown: `engine-output`
- `available` state depends on real evidence and must not be inferred from a hidden worker-local path
- object references remain logical identifiers only, currently using `artifact://tasks/<task-id>/<artifact-id>` for worker-registered rows
- size and checksum enrichment is limited to safe in-memory evidence such as captured `stdout`, captured `stderr`, or persisted `raw_report`

External clients should continue to treat `download_available=false` as authoritative even when a persisted row is `available`.

## Engine Parameter Mapping Contract

Worker execution mapping is experimental runtime behavior.

k6 receives execution metadata through environment variables such as `DURATION_SECONDS`, `RAMP_UP_SECONDS`, `RAMP_DOWN_SECONDS`, `GRACEFUL_STOP_SECONDS`, `ITERATION_LIMIT`, `STOP_POLICY`, and `DATA_POLICY`.

k6 receives shard metadata through `SHARD_ID`, `DATASET_SOURCE`, `DATASET_FORMAT`, `DATASET_OFFSET`, and `DATASET_LIMIT`.

JMeter receives execution metadata through `-Jduration_seconds`, `-Jramp_up_seconds`, `-Jramp_down_seconds`, `-Jstop_policy`, `-Jgraceful_stop_seconds`, and `-Jiteration_limit`.

JMeter receives shard metadata through `-Jshard_id`, `-Jdataset_source`, `-Jdataset_format`, `-Jdataset_offset`, and `-Jdataset_limit`.

External clients should not rely on worker internals beyond the documented task, shard, and result contracts.

## Artifact Convention

Artifact handling is planning-only in the Core contract. Current dataset source fields are placeholder-safe references:

- `artifact://...` for managed artifacts or datasets that a future artifact layer can resolve
- `inline://...` for small inline or synthetic references

The current runtime validates source shape and now documents an artifact lifecycle contract, but it does not implement a full artifact browser API, artifact storage API, dataset resolver, or durable artifact store.

## Stable, Experimental, And Planning-Only Fields

| Classification | Current Items | Compatibility Expectation |
|---|---|---|
| Stable candidate | `GET /api/tasks/`, `GET /api/tasks/{id}/`, `GET /api/tasks/templates/`, `GET /api/tasks/templates/coverage/`, template metadata, coverage metadata | Additive changes only where possible; clients should ignore unknown fields. |
| Experimental runtime contract | `execution`, `distribution`, `GET /api/tasks/{id}/shard-plan/`, `GET /api/tasks/{id}/result-summary/`, `GET /api/tasks/{id}/artifacts/`, `GET /api/tasks/{id}/artifacts/{artifact_id}/download/`, worker execution mapping, shard metadata mapping | Implemented in preview runtime but still subject to shape refinement before `/api/v1`. |
| Planning-only | token API, advanced distributed scheduler, advanced result aggregation, durable artifact download, report generation | Documented for direction only; clients should not depend on runtime availability. |

## Compatibility Rules

- Add optional response fields instead of renaming existing fields.
- Keep existing documented enum values valid unless a deprecation path is documented.
- Prefer new fields or new endpoints for materially different behavior.
- Preserve template identifiers unless a migration path is documented.
- Keep coverage summary semantics stable when profile counts change.
- Mark preview-only behavior clearly when it is not yet a stable versioned contract.

## Non-Goals

- This contract does not define a complete `/api/v1` implementation.
- This contract does not add token scopes or access-control behavior.
- This contract does not add a dashboard UI.
- This contract does not add distributed scheduling, worker claim, shard retry, or shard persistence.
- This contract does not add dataset loading or artifact storage.
- This contract does not add real artifact download or report generation.
- This contract does not define exact percentile aggregation.
