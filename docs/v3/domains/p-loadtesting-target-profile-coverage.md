# pLoadtesting Target Profile Coverage

This document is the authoritative profile-level coverage matrix for the current `target-apps` catalog.

## Summary

- Target Apps: `10`
- Profile Count: `44`
- k6 Profile Count: `22`
- JMeter Profile Count: `22`
- Exact Pair Count: `22`
- Strict Non-Parity Count: `0`

## Counting Rules

- Profile parity is tracked at the `target_profile_id` level, not only at the target-family level.
- `equivalent_profile_id` in `target-apps/task-templates/*.yaml` is the source of truth for 1:1 engine parity.
- Exact parity requires:
  - reciprocal `equivalent_profile_id`
  - opposite engines
  - same `target_app_id`
- Unmatched retained profiles still count in the strict totals.
- `coverage_status` is computed by the Control Plane template registry from reciprocal `equivalent_profile_id` metadata.
- `coverage_group` is a deterministic dashboard grouping key such as `payload.download`.
- `coverage_gap` is null for exact coverage and contains a short explanation when a profile has no exact equivalent.
- The current strict non-parity set is empty.

## Target App Catalog

| Target App | Endpoint Family | Profile Count | Parity Summary |
|---|---|---:|---|
| `echo-api` | health + echo | 2 | `1` exact pair |
| `latency-api` | delay + timeout simulation | 2 | `1` exact pair |
| `error-api` | status + flaky + 429 | 2 | `1` exact pair |
| `resource-api` | CPU + memory + I/O | 2 | `1` exact pair |
| `payload-api` | download + file + archive + tar/selective | 10 | `5` exact pairs |
| `crud-api` | create + list + fetch item | 2 | `1` exact pair |
| `auth-flow-api` | checkout + refresh + failure + session + mfa | 10 | `5` exact pairs |
| `sse-api` | events + ticker + progress-heavy | 6 | `3` exact pairs |
| `ws-api` | echo + broadcast | 4 | `2` exact pairs |
| `db-api` | CRUD + list/filter | 4 | `2` exact pairs |

## Full Matrix

| Target App | Endpoint Family | Profile ID | Engine | Sample File | Equivalent Profile | 1:1 Coverage | Gap | Recommend Backfill | Priority |
|---|---|---|---|---|---|---|---|---|---|
| `echo-api` | echo smoke | `echo-k6-smoke` | `k6` | `engines/k6/target_apps_echo_smoke.js` | `echo-jmeter-smoke` | yes | none | no | none |
| `echo-api` | echo smoke | `echo-jmeter-smoke` | `jmeter` | `engines/jmeter/target_apps_echo_latency_plan.jmx` | `echo-k6-smoke` | yes | none | no | none |
| `latency-api` | delay | `latency-k6-delay` | `k6` | `engines/k6/target_apps_latency_delay.js` | `latency-jmeter-delay` | yes | none | no | none |
| `latency-api` | delay | `latency-jmeter-delay` | `jmeter` | `engines/jmeter/target_apps_echo_latency_plan.jmx` | `latency-k6-delay` | yes | none | no | none |
| `error-api` | flaky failure branch | `error-k6-flaky` | `k6` | `engines/k6/target_apps_error_flaky.js` | `error-jmeter-flaky` | yes | none | no | none |
| `error-api` | flaky failure branch | `error-jmeter-flaky` | `jmeter` | `engines/jmeter/target_apps_echo_latency_plan.jmx` | `error-k6-flaky` | yes | none | no | none |
| `resource-api` | cpu | `resource-k6-cpu` | `k6` | `engines/k6/target_apps_resource_cpu.js` | `resource-jmeter-cpu` | yes | none | no | none |
| `resource-api` | cpu | `resource-jmeter-cpu` | `jmeter` | `engines/jmeter/target_apps_echo_latency_plan.jmx` | `resource-k6-cpu` | yes | none | no | none |
| `payload-api` | generic text download | `payload-k6-download` | `k6` | `engines/k6/target_apps_payload_download.js` | `payload-jmeter-download` | yes | none | no | none |
| `payload-api` | generic text download | `payload-jmeter-download` | `jmeter` | `engines/jmeter/target_apps_payload_crud_plan.jmx` | `payload-k6-download` | yes | none | no | none |
| `payload-api` | fixture file download | `payload-k6-file-download` | `k6` | `engines/k6/target_apps_payload_file_flow.js` | `payload-jmeter-file-download` | yes | none | no | none |
| `payload-api` | fixture file download | `payload-jmeter-file-download` | `jmeter` | `engines/jmeter/target_apps_payload_flow_plan.jmx` | `payload-k6-file-download` | yes | none | no | none |
| `payload-api` | file roundtrip | `payload-k6-file-roundtrip` | `k6` | `engines/k6/target_apps_payload_file_flow.js` | `payload-jmeter-file-roundtrip` | yes | none | no | none |
| `payload-api` | file roundtrip | `payload-jmeter-file-roundtrip` | `jmeter` | `engines/jmeter/target_apps_payload_flow_plan.jmx` | `payload-k6-file-roundtrip` | yes | none | no | none |
| `payload-api` | archive read-many | `payload-k6-archive-read-many` | `k6` | `engines/k6/target_apps_payload_archive_flow.js` | `payload-jmeter-archive-read-many` | yes | none | no | none |
| `payload-api` | archive read-many | `payload-jmeter-archive-read-many` | `jmeter` | `engines/jmeter/target_apps_payload_flow_plan.jmx` | `payload-k6-archive-read-many` | yes | none | no | none |
| `payload-api` | tar selective fetch | `payload-k6-tar-selective-fetch` | `k6` | `engines/k6/target_apps_payload_tar_selective_flow.js` | `payload-jmeter-tar-selective-fetch` | yes | none | no | none |
| `payload-api` | tar selective fetch | `payload-jmeter-tar-selective-fetch` | `jmeter` | `engines/jmeter/target_apps_payload_flow_plan.jmx` | `payload-k6-tar-selective-fetch` | yes | none | no | none |
| `crud-api` | create and fetch | `crud-k6-flow` | `k6` | `engines/k6/target_apps_crud_flow.js` | `crud-jmeter-flow` | yes | none | no | none |
| `crud-api` | create and fetch | `crud-jmeter-flow` | `jmeter` | `engines/jmeter/target_apps_crud_flow_plan.jmx` | `crud-k6-flow` | yes | none | no | none |
| `auth-flow-api` | checkout | `auth-k6-checkout` | `k6` | `engines/k6/target_apps_auth_checkout.js` | `auth-jmeter-checkout` | yes | none | no | none |
| `auth-flow-api` | checkout | `auth-jmeter-checkout` | `jmeter` | `engines/jmeter/target_apps_auth_flow_plan.jmx` | `auth-k6-checkout` | yes | none | no | none |
| `auth-flow-api` | refresh | `auth-k6-refresh-flow` | `k6` | `engines/k6/target_apps_auth_refresh_flow.js` | `auth-jmeter-refresh-flow` | yes | none | no | none |
| `auth-flow-api` | refresh | `auth-jmeter-refresh-flow` | `jmeter` | `engines/jmeter/target_apps_auth_flow_plan.jmx` | `auth-k6-refresh-flow` | yes | none | no | none |
| `auth-flow-api` | failure branches | `auth-k6-failure-branches` | `k6` | `engines/k6/target_apps_auth_refresh_flow.js` | `auth-jmeter-failure-branches` | yes | none | no | none |
| `auth-flow-api` | failure branches | `auth-jmeter-failure-branches` | `jmeter` | `engines/jmeter/target_apps_auth_flow_plan.jmx` | `auth-k6-failure-branches` | yes | none | no | none |
| `auth-flow-api` | session | `auth-k6-session-flow` | `k6` | `engines/k6/target_apps_auth_session_mfa_flow.js` | `auth-jmeter-session-flow` | yes | none | no | none |
| `auth-flow-api` | session | `auth-jmeter-session-flow` | `jmeter` | `engines/jmeter/target_apps_auth_flow_plan.jmx` | `auth-k6-session-flow` | yes | none | no | none |
| `auth-flow-api` | mfa | `auth-k6-mfa-flow` | `k6` | `engines/k6/target_apps_auth_session_mfa_flow.js` | `auth-jmeter-mfa-flow` | yes | none | no | none |
| `auth-flow-api` | mfa | `auth-jmeter-mfa-flow` | `jmeter` | `engines/jmeter/target_apps_auth_flow_plan.jmx` | `auth-k6-mfa-flow` | yes | none | no | none |
| `sse-api` | events smoke | `sse-k6-smoke` | `k6` | `engines/k6/target_apps_sse_smoke.js` | `sse-jmeter-smoke` | yes | none | no | none |
| `sse-api` | events smoke | `sse-jmeter-smoke` | `jmeter` | `engines/jmeter/target_apps_sse_plan.jmx` | `sse-k6-smoke` | yes | none | no | none |
| `sse-api` | ticker | `sse-k6-ticker` | `k6` | `engines/k6/target_apps_sse_smoke.js` | `sse-jmeter-ticker` | yes | none | no | none |
| `sse-api` | ticker | `sse-jmeter-ticker` | `jmeter` | `engines/jmeter/target_apps_sse_plan.jmx` | `sse-k6-ticker` | yes | none | no | none |
| `sse-api` | progress-heavy | `sse-k6-progress-heavy` | `k6` | `engines/k6/target_apps_sse_smoke.js` | `sse-jmeter-progress-heavy` | yes | none | no | none |
| `sse-api` | progress-heavy | `sse-jmeter-progress-heavy` | `jmeter` | `engines/jmeter/target_apps_sse_plan.jmx` | `sse-k6-progress-heavy` | yes | none | no | none |
| `ws-api` | echo | `ws-k6-echo-smoke` | `k6` | `engines/k6/target_apps_ws_echo_smoke.js` | `ws-jmeter-echo-smoke` | yes | none | no | none |
| `ws-api` | echo | `ws-jmeter-echo-smoke` | `jmeter` | `engines/jmeter/target_apps_ws_flow_plan.jmx` | `ws-k6-echo-smoke` | yes | none | no | none |
| `ws-api` | broadcast | `ws-k6-broadcast-smoke` | `k6` | `engines/k6/target_apps_ws_broadcast_smoke.js` | `ws-jmeter-broadcast-smoke` | yes | none | no | none |
| `ws-api` | broadcast | `ws-jmeter-broadcast-smoke` | `jmeter` | `engines/jmeter/target_apps_ws_flow_plan.jmx` | `ws-k6-broadcast-smoke` | yes | none | no | none |
| `db-api` | crud smoke | `db-k6-crud-smoke` | `k6` | `engines/k6/target_apps_db_crud_flow.js` | `db-jmeter-crud-smoke` | yes | none | no | none |
| `db-api` | crud smoke | `db-jmeter-crud-smoke` | `jmeter` | `engines/jmeter/target_apps_db_flow_plan.jmx` | `db-k6-crud-smoke` | yes | none | no | none |
| `db-api` | list filter | `db-k6-list-filter` | `k6` | `engines/k6/target_apps_db_list_filter.js` | `db-jmeter-list-filter` | yes | none | no | none |
| `db-api` | list filter | `db-jmeter-list-filter` | `jmeter` | `engines/jmeter/target_apps_db_flow_plan.jmx` | `db-k6-list-filter` | yes | none | no | none |

## Gap Summary

Current strict non-parity profiles: none.

The former `payload-jmeter-download` gap is closed by `payload-k6-download`, a low-cost exact k6 peer for `GET /api/download?kb=32`.

## Machine-Readable Coverage Export

Dashboard and API consumers should use:

```text
GET /api/tasks/templates/coverage/
```

The export includes:

- `summary`: target, profile, engine, exact coverage, and gap counts
- `targets`: per-target profile and coverage aggregates
- `profiles`: profile-level script, engine, equivalent profile, and coverage metadata
- `gaps`: currently empty because every profile has reciprocal exact coverage

## Verification Notes

- Template parity metadata is validated in `target-apps/tests/test_suite.py`.
- Control Plane template listing and task expansion are validated in `control-plane/apps/tasks/tests.py`.
- Runtime execution parity remains bounded and local-only through the current k6, JMeter, and Docker smoke validation paths.
- The machine-readable coverage export is validated through Control Plane API tests.
