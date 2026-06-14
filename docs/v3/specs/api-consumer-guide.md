# API Consumer Guide

This guide documents how external tools can consume the current preview Control Plane API without reading repository internals. It is an integration guide only; it does not add new API behavior.

## Base URL And Access

Use the Control Plane base URL for the environment:

```text
http://127.0.0.1:9000
```

The current preview access mechanism is the shared `PLOADTESTING_API_TOKEN` compatibility layer. Use a placeholder in examples and replace it only in the local execution environment:

```bash
export PLOADTESTING_API_TOKEN="<API_TOKEN>"
```

Preview requests can pass the token header:

```bash
curl -sS \
  -H "X-PLOADTESTING-API-TOKEN: ${PLOADTESTING_API_TOKEN}" \
  http://127.0.0.1:9000/api/tasks/templates/coverage/
```

Scoped API tokens are future work and are specified separately in [API token access planning spec](api-token-auth.md).

## Read Template Profiles

Use `GET /api/tasks/templates/` to list selectable task profiles.

```bash
curl -sS \
  -H "X-PLOADTESTING-API-TOKEN: ${PLOADTESTING_API_TOKEN}" \
  http://127.0.0.1:9000/api/tasks/templates/
```

Each profile row includes:

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

## Read Coverage Metadata

Use `GET /api/tasks/templates/coverage/` for dashboard cards, coverage matrices, and target/profile counts.

```bash
curl -sS \
  -H "X-PLOADTESTING-API-TOKEN: ${PLOADTESTING_API_TOKEN}" \
  http://127.0.0.1:9000/api/tasks/templates/coverage/
```

Response sections:

- `summary`: total target, profile, engine, exact coverage, and gap counts
- `targets`: per-target catalog and aggregate coverage data
- `profiles`: one row per profile with coverage metadata
- `gaps`: profiles whose `coverage_status` is `gap`

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

`coverage_status=exact` means the profile has a reciprocal `equivalent_profile_id` on the opposite engine within the same target app. `coverage_status=gap` means `coverage_gap` contains the reason exact parity is not currently available.

## Create A Task From A Profile

Prefer manifest-driven task creation over free-form script paths:

```bash
curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-PLOADTESTING-API-TOKEN: ${PLOADTESTING_API_TOKEN}" \
  -d @docs/v3/specs/examples/create-task-from-profile.json \
  http://127.0.0.1:9000/api/tasks/
```

Minimum request:

```json
{
  "target_app_id": "payload-api",
  "target_profile_id": "payload-k6-download",
  "created_by": "api-consumer-guide"
}
```

When `target_app_id` and `target_profile_id` are provided, the Control Plane expands the template into the existing task fields: `name`, `engine`, `script_path`, `target_url`, and default `parameters`.

## Error Handling

Current preview endpoints use Django REST Framework error responses. Consumers should handle:

| Status | Typical Meaning |
|---|---|
| `400` | Invalid task creation input or unknown template profile |
| `403` | Missing or invalid preview token |
| `404` | Task or route not found |
| `409` | Duplicate result submission for a task |
| `5xx` | Control Plane runtime failure |

Future `/api/v1` work should normalize errors into the stable shape described in [External API v1 planning spec](external-api-v1.md).

## Stable And Preview Fields

Stable enough for dashboard and API consumers:

- `target_app_id`
- `target_profile_id`
- `engine`
- `script_path`
- `target_url`
- `equivalent_profile_id`
- `coverage_status`
- `coverage_group`
- `coverage_gap`
- coverage summary counts

Preview and subject to future tightening:

- detailed `safe_limits` keys
- per-script parameter names
- inline `raw_report` shape
- future `/api/v1` route names

## Example Files

Example JSON files are stored in [examples/](examples/):

- [templates-coverage-response.json](examples/templates-coverage-response.json)
- [task-template-profile.json](examples/task-template-profile.json)
- [create-task-from-profile.json](examples/create-task-from-profile.json)

The coverage response example is shortened for readability but preserves the current response shape.
