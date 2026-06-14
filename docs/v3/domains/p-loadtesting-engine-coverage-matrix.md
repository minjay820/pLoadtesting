# pLoadtesting Engine Coverage Matrix

This matrix tracks manifest-driven target profiles across `k6` and `jmeter`.

Current policy:

- every current `k6` target profile should have a matching `jmeter` profile
- the preferred state is `exact`, not only target-family correspondence
- when a profile is still only approximately covered, it should be called out explicitly and queued for backfill

## Current Matrix

| Target App | k6 Profile | JMeter Profile | Relation | Notes |
|---|---|---|---|---|
| `echo-api` | `echo-k6-smoke` | `echo-jmeter-smoke` | exact | GET echo smoke |
| `latency-api` | `latency-k6-delay` | `latency-jmeter-delay` | exact | bounded delay endpoint |
| `error-api` | `error-k6-flaky` | `error-jmeter-flaky` | exact | deterministic flaky failure branch |
| `resource-api` | `resource-k6-cpu` | `resource-jmeter-cpu` | exact | bounded CPU request |
| `crud-api` | `crud-k6-flow` | `crud-jmeter-flow` | exact | create and fetch item |
| `auth-flow-api` | `auth-k6-checkout` | `auth-jmeter-checkout` | exact | login, profile, checkout |
| `auth-flow-api` | `auth-k6-refresh-flow` | `auth-jmeter-refresh-flow` | exact | expiry, refresh, logout |
| `auth-flow-api` | `auth-k6-failure-branches` | `auth-jmeter-failure-branches` | exact | invalid credential plus expiry/revocation checks |
| `auth-flow-api` | `auth-k6-session-flow` | `auth-jmeter-session-flow` | exact | cookie session flow |
| `auth-flow-api` | `auth-k6-mfa-flow` | `auth-jmeter-mfa-flow` | exact | deterministic MFA-like flow |
| `sse-api` | `sse-k6-smoke` | `sse-jmeter-smoke` | exact | bounded events stream |
| `sse-api` | `sse-k6-ticker` | `sse-jmeter-ticker` | exact | bounded ticker stream |
| `sse-api` | `sse-k6-progress-heavy` | `sse-jmeter-progress-heavy` | exact | richer bounded progress stream |
| `payload-api` | `payload-k6-file-download` | `payload-jmeter-file-download` | exact | fixture file download |
| `payload-api` | `payload-k6-file-roundtrip` | `payload-jmeter-file-roundtrip` | exact | manifest, download, upload roundtrip |
| `payload-api` | `payload-k6-archive-read-many` | `payload-jmeter-archive-read-many` | exact | fixture-pack, zip archive, read-many |
| `payload-api` | `payload-k6-tar-selective-fetch` | `payload-jmeter-tar-selective-fetch` | exact | manifest-driven selective subset plus tar-like package |
| `ws-api` | `ws-k6-echo-smoke` | `ws-jmeter-echo-smoke` | exact | bounded echo connection |
| `ws-api` | `ws-k6-broadcast-smoke` | `ws-jmeter-broadcast-smoke` | exact | bounded room broadcast |
| `db-api` | `db-k6-crud-smoke` | `db-jmeter-crud-smoke` | exact | SQLite create and fetch |
| `db-api` | `db-k6-list-filter` | `db-jmeter-list-filter` | exact | SQLite list and filter |

## Non-Paired Generic Profiles

These JMeter profiles still exist because they are useful operational shortcuts, but they are not the profile-to-profile mirror used by the exact matrix above:

| Target App | JMeter Profile | Role |
|---|---|---|
| `payload-api` | `payload-jmeter-download` | generic text payload download |

## Verification Notes

- Template asset existence and engine coverage are tested in `target-apps/tests/test_suite.py`.
- Template expansion into Control Plane task fields is tested in `control-plane/apps/tasks/tests.py`.
- Representative JMeter runtime validation is still done through local CLI runs and the Docker smoke path, not through always-on CI for every JMX file.
