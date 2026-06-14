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

## Planned Execution And Distribution Objects

The current preview API does not yet implement duration-based execution or distributed multi-agent execution. Future `/api/v1/tasks` should accept these objects:

| Object | Purpose |
|---|---|
| `execution` | Duration, ramp-up, ramp-down, stop policy, grace period, worker timeout, iteration limit, and data policy. |
| `distribution` | Single-agent or sharded execution mode, claim model, agent selectors, and shard definitions. |
| `dataset` | Dataset source, format, partition strategy, and shard ranges. |
| `shards` | Per-shard execution and dataset assignment under `distribution`. |
| `result_aggregation` | Read-only result object describing global and per-shard aggregation confidence. |

Consumers should follow [Task execution model](task-execution-model.md) and [Distributed agent execution](distributed-agent-execution.md) when preparing future-compatible payloads.

Planned single-agent 10-minute task:

```json
{
  "target_app_id": "payload-api",
  "target_profile_id": "payload-k6-download",
  "created_by": "api-consumer-guide",
  "execution": {
    "duration_seconds": 600,
    "ramp_up_seconds": 30,
    "ramp_down_seconds": 30,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 720,
    "iteration_limit": null,
    "data_policy": "time_bounded"
  },
  "distribution": {
    "mode": "single_agent"
  }
}
```

Planned single-agent 1-hour graceful task:

```json
{
  "target_app_id": "latency-api",
  "target_profile_id": "latency-k6-delay",
  "created_by": "api-consumer-guide",
  "execution": {
    "duration_seconds": 3600,
    "ramp_up_seconds": 120,
    "ramp_down_seconds": 60,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 60,
    "max_run_seconds": 3900,
    "iteration_limit": null,
    "data_policy": "time_bounded"
  },
  "distribution": {
    "mode": "single_agent"
  }
}
```

Planned multi-agent dataset split:

```json
{
  "target_app_id": "db-api",
  "target_profile_id": "db-k6-list-filter",
  "created_by": "api-consumer-guide",
  "execution": {
    "duration_seconds": 1800,
    "stop_policy": "whichever_first",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 2100,
    "data_policy": "whichever_first"
  },
  "dataset": {
    "source": "artifact://datasets/users.csv",
    "format": "csv",
    "partition_strategy": "manual_ranges",
    "shards": [
      {
        "shard_id": "users-a",
        "offset": 0,
        "limit": 2000
      },
      {
        "shard_id": "users-b",
        "offset": 2000,
        "limit": 3000
      }
    ]
  },
  "distribution": {
    "mode": "sharded",
    "claim_model": "agent_claim",
    "shards": [
      {
        "shard_id": "users-a",
        "agent_selector": {
          "engine": "k6",
          "labels": {
            "target_network": "internal-a"
          }
        },
        "dataset_shard": {
          "offset": 0,
          "limit": 2000
        }
      },
      {
        "shard_id": "users-b",
        "agent_selector": {
          "engine": "k6",
          "labels": {
            "target_network": "internal-a"
          }
        },
        "dataset_shard": {
          "offset": 2000,
          "limit": 3000
        }
      }
    ]
  }
}
```

Planned multi-agent target network labels:

```json
{
  "target_app_id": "payload-api",
  "target_profile_id": "payload-jmeter-download",
  "created_by": "api-consumer-guide",
  "execution": {
    "duration_seconds": 900,
    "stop_policy": "graceful_stop",
    "graceful_stop_seconds": 30,
    "max_run_seconds": 1020,
    "data_policy": "time_bounded"
  },
  "distribution": {
    "mode": "sharded",
    "claim_model": "agent_claim",
    "shards": [
      {
        "shard_id": "network-a",
        "agent_selector": {
          "engine": "jmeter",
          "labels": {
            "target_network": "internal-a"
          }
        }
      },
      {
        "shard_id": "network-b",
        "agent_selector": {
          "engine": "jmeter",
          "labels": {
            "target_network": "internal-b"
          }
        }
      }
    ]
  }
}
```

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
- `execution`, `distribution`, `dataset`, `shards`, and `result_aggregation` until the v1 runtime contract is implemented

## Example Files

Example JSON files are stored in [examples/](examples/):

- [templates-coverage-response.json](examples/templates-coverage-response.json)
- [task-template-profile.json](examples/task-template-profile.json)
- [create-task-from-profile.json](examples/create-task-from-profile.json)

The coverage response example is shortened for readability but preserves the current response shape.
