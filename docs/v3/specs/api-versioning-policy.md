# API Versioning Policy

This document defines the Core API compatibility policy for preview APIs, future versioned APIs, template metadata, and external client integrations.

## Versioning Approach

The current runtime exposes preview endpoints under `/api/`. These endpoints are implemented and usable for local preview and integration development, but they are not yet a final stable versioned contract.

Future stable external APIs should use `/api/v1/` route families. The `/api/v1/` contract should be introduced as an additive layer that maps to the same Core concepts: tasks, task templates, coverage metadata, workers, results, execution metadata, distribution metadata, and shard plans.

Preview clients should use [API consumer guide](api-consumer-guide.md) and [External client contract](external-client-contract.md) for current behavior.

## Field Classifications

| Classification | Meaning |
|---|---|
| Stable candidate | Current preview behavior that is expected to become stable with minimal shape changes. |
| Experimental runtime contract | Implemented preview behavior that works now but can still be refined before `/api/v1`. |
| Planning-only | Documented direction that does not imply current runtime support. |

## Stable Candidate Fields

The following are stable candidate contracts:

- `GET /api/tasks/`
- `GET /api/tasks/{id}/`
- `GET /api/tasks/templates/`
- `GET /api/tasks/templates/coverage/`
- Task history and task detail read-model fields.
- Template metadata rows.
- Coverage metadata summary, target rows, profile rows, and gap rows.

Compatibility expectations:

- Preserve existing documented field names where possible.
- Add optional fields rather than changing field meaning.
- Keep target and profile identifiers stable unless a migration path is documented.
- Keep coverage summary semantics stable even when counts change.

## Experimental Runtime Contracts

The following are experimental runtime contracts:

- `execution` on `POST /api/tasks/`.
- `distribution` on `POST /api/tasks/`.
- `GET /api/tasks/{id}/shard-plan/`.
- `GET /api/tasks/{id}/result-summary/`.
- `GET /api/tasks/{id}/artifacts/`.
- `GET /api/tasks/{id}/artifacts/{artifact_id}/download/`.
- Persisted artifact manifest metadata and controlled object references.
- Artifact manifest version `1.0` and worker artifact registration payload compatibility.
- Worker execution mapping for k6 and JMeter.
- Worker shard metadata mapping for k6 and JMeter.

Compatibility expectations:

- Treat these fields as implemented preview behavior.
- Avoid client assumptions beyond documented schema, validation rules, and mapping.
- Expect additive metadata and possible `/api/v1` naming refinements before stabilization.
- Keep existing MVP enum values valid unless a deprecation path is documented.
- Preserve artifact item shape even as persisted manifest metadata expands behind the same response contract.
- Preserve backward compatibility for legacy list-only worker artifact payloads while preferring the versioned envelope shape.
- Treat unsupported future artifact manifest versions as explicit validation failures until a migration path is documented.

## Planning-Only Contracts

The following are planning-only:

- Scoped token API.
- Advanced distributed scheduler.
- Worker claim lifecycle.
- Advanced result aggregation.
- Durable artifact download and full artifact browser API.
- Dataset resolver and durable artifact storage lifecycle.

Planning-only content should not be treated as runtime availability. External clients can use these documents for roadmap alignment, but production integration should depend only on implemented endpoints and explicit stable candidates.

## Additive Change Policy

Core can add:

- Optional response fields.
- Optional request fields with default behavior.
- New enum values when old values remain valid.
- New endpoints.
- New template metadata fields.
- New coverage metadata dimensions.
- New optional artifact metadata fields such as checksum, size, or contract metadata.

External clients should ignore unknown response fields and should avoid strict schema rejection for additional optional fields.

## Breaking Change Policy

Breaking changes include:

- Removing a documented field.
- Renaming a documented field.
- Changing the type of a documented field.
- Changing the meaning of an existing enum value.
- Removing a documented endpoint without a replacement.
- Changing template identifier semantics without a migration path.

Breaking changes should be avoided in stable candidate areas and should require a documented migration path before `/api/v1` stabilization.

## Deprecation Policy

When a field or endpoint needs replacement:

1. Add the replacement first.
2. Document the old and new shape.
3. Keep the old field or endpoint through a documented migration window.
4. Mark examples and consumer docs to prefer the replacement.
5. Remove the old shape only after the compatibility window is complete.

Preview-only fields can be refined more quickly than stable candidate fields, but the change should still be documented in `docs/v3/` and the daily log.

## Schema Compatibility

Schema compatibility rules:

- Use integers for duration, ramp, timeout, dataset offset, and dataset limit fields.
- Use strings for identifiers, enum values, URLs, paths, and placeholder-safe artifact references.
- Use arrays for label lists.
- Use objects for nested metadata such as `execution`, `distribution`, `agent_selector`, `dataset`, and `result_aggregation`.
- Prefer `null` for intentionally absent optional values rather than overloading empty strings.

## Template Metadata Compatibility

Template metadata is a primary integration surface for external clients. Core should preserve:

- `target_app_id`
- `target_profile_id`
- `engine`
- `script_path`
- `target_url`
- `equivalent_profile_id`
- `coverage_status`
- `coverage_group`

New template fields should be optional and documented. Template consumers should not require every profile to define optional runtime defaults such as `execution`.

## External Client Compatibility

External clients should:

- Create tasks through documented HTTP APIs.
- Prefer template identifiers over direct internal script discovery.
- Read coverage through `GET /api/tasks/templates/coverage/`.
- Read run history through `GET /api/tasks/`.
- Read result summary through `GET /api/tasks/{id}/result-summary/` and handle `not_available` as a normal waiting state.
- Read artifact metadata through `GET /api/tasks/{id}/artifacts/` and treat `planned`, `available`, and `missing` states as the runtime-supported lifecycle.
- Treat `GET /api/tasks/{id}/artifacts/{artifact_id}/download/` as a preview placeholder route until a durable download policy is documented.
- Read manual shard plans through `GET /api/tasks/{id}/shard-plan/` when a task uses distribution metadata.
- Avoid importing internal Python functions or relying on undocumented file layout.
- Treat any downstream requirement as a request for a generic Core capability.

Core should:

- Avoid naming or depending on any specific external client implementation.
- Keep public contracts neutral and reusable.
- Document runtime support separately from planning-only roadmap items.
- Keep future `/api/v1` compatibility aligned with current stable candidate contracts.
- Preserve result provenance semantics so clients can distinguish stored task metrics from future aggregate metrics.

## Examples

Stable candidate example:

```text
GET /api/tasks/templates/
GET /api/tasks/templates/coverage/
GET /api/tasks/
GET /api/tasks/{id}/
```

Experimental runtime example:

```json
{
  "execution": {
    "duration_seconds": 600,
    "stop_policy": "graceful_stop",
    "max_run_seconds": 720,
    "data_policy": "duration_first"
  }
}
```

Experimental distribution example:

```json
{
  "distribution": {
    "mode": "manual_shards",
    "result_merge_policy": "summary_only",
    "shards": [
      {
        "shard_id": "users-a",
        "agent_selector": {
          "labels": ["zone:a", "engine:k6"]
        },
        "dataset": {
          "source": "artifact://datasets/users.csv",
          "format": "csv",
          "offset": 0,
          "limit": 2000
        }
      }
    ]
  }
}
```

Planning-only example:

```text
/api/v1/artifacts/
advanced distributed scheduler
exact percentile merge
report generation
```
