# pLoadtesting Engine Coverage Matrix

This document now acts as a short bridge page for engine parity.

## Current Position

- Exact k6↔JMeter parity is now tracked through `equivalent_profile_id` in `target-apps/task-templates/*.yaml`.
- The full authoritative matrix lives in [p-loadtesting-target-profile-coverage.md](p-loadtesting-target-profile-coverage.md).
- The current strict totals are:
  - `21` exact pair rows
  - `1` strict non-parity profile

## Exact Pairs At A Glance

| Target App | Exact Pair Rows |
|---|---:|
| `echo-api` | 1 |
| `latency-api` | 1 |
| `error-api` | 1 |
| `resource-api` | 1 |
| `payload-api` | 4 |
| `crud-api` | 1 |
| `auth-flow-api` | 5 |
| `sse-api` | 3 |
| `ws-api` | 2 |
| `db-api` | 2 |

## Remaining Gap

| Profile ID | Status |
|---|---|
| `payload-jmeter-download` | retained generic JMeter shortcut without a strict k6 peer |

## Verification Notes

- Template parity metadata is validated in `target-apps/tests/test_suite.py`.
- Control Plane template listing and task expansion are validated in `control-plane/apps/tasks/tests.py`.
- Runtime execution checks remain bounded and local through k6, JMeter, and Docker smoke validation.
