# engines/jmeter

This directory contains JMeter plans for `pLoadtesting`, including the original reference target plan and target-suite sample plans used by manifest-driven task templates.

## Plans

| Plan | Purpose |
|---|---|
| `ploadtesting_test_plan.jmx` | Original reference target plan for the legacy `target-app/` endpoints |
| `target_apps_echo_latency_plan.jmx` | Generic GET-oriented plan for echo, latency, error, and resource smoke requests |
| `target_apps_payload_crud_plan.jmx` | Generic GET-oriented plan for payload, CRUD listing, and archive/read-many style requests |
| `target_apps_crud_flow_plan.jmx` | Exact create-and-fetch CRUD flow for `crud-api` |
| `target_apps_payload_flow_plan.jmx` | Exact payload file download, roundtrip, archive/read-many, and tar/selective flows |
| `target_apps_sse_plan.jmx` | Bounded finite SSE validation using a JSR223 sampler and the Java 11 HTTP client |
| `target_apps_auth_flow_plan.jmx` | Demo-only auth refresh, session, and MFA-like flows using a JSR223 sampler |
| `target_apps_ws_flow_plan.jmx` | Bounded WebSocket echo and broadcast validation using the Java 11 WebSocket client |
| `target_apps_db_flow_plan.jmx` | SQLite-backed DB CRUD or list/filter validation using a JSR223 sampler |

## Coverage Notes

- The current target catalog now has selective JMeter coverage for every target family.
- The repo baseline is now: every current target family should have at least one `k6` and one `jmeter` sample asset.
- Exact profile-to-profile pairing for current manifest-driven target profiles is tracked in `docs/v3/domains/p-loadtesting-engine-coverage-matrix.md`.
- SSE and WebSocket plans do not require third-party JMeter websocket plugins in this repo phase; they use Groovy plus the Java 11 built-in HTTP and WebSocket clients.

## Common Parameters

The Worker now passes template parameters to JMeter as `-J...` properties, so the same values defined in `target-apps/task-templates/*.yaml` are available inside the plans.

Common properties:

- `TARGET_HOST`
- `TARGET_PORT`
- `TARGET_PATH`
- `TARGET_METHOD`
- `TARGET_QUERY`
- `target_url`

Flow-specific properties depend on the plan, for example:

- SSE: `SSE_ENDPOINT_PATH`, `SSE_COUNT`, `SSE_STEPS`, `SSE_INTERVAL_MS`
- payload: `FLOW_MODE`, `FILE_ENDPOINT_PATH`, `FILE_KB`, `PACK_COUNT`, `PACK_KB_PER_FILE`, `SELECTIVE_COUNT`
- auth: `FLOW_MODE`, `DEMO_USERNAME`, `DEMO_PASSWORD`, `ACCESS_TOKEN_USES`, `REFRESH_USES`, `SESSION_USES`, `MFA_CHANNEL`, `MFA_ISSUE_MODE`
- WebSocket: `FLOW_MODE`, `WS_PATH`, `WS_ROOM`, `WS_MESSAGE`, `WS_CLIENT_ID`
- DB-heavy: `FLOW_MODE`, `DB_RECORD_*`, `DB_LIST_*`
- CRUD: `ITEM_NAME`, `ITEM_VALUE`

## Run Examples

Prerequisites:

- Apache JMeter `5.5+`
- Java `11+`

Verify the CLI:

```bash
jmeter --version
```

Generic GET example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_echo_latency_plan.jmx \
  -JTARGET_HOST=127.0.0.1 \
  -JTARGET_PORT=18082 \
  -JTARGET_PATH=/api/flaky \
  -JTARGET_METHOD=GET \
  -JTARGET_QUERY='rate=0.5&deterministic=true&request_key=ci' \
  -JEXPECTED_STATUS_PREFIX=5
```

SSE example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_sse_plan.jmx \
  -JSSE_ENDPOINT_PATH=/api/progress-heavy \
  -JSSE_STEPS=24 \
  -JSSE_INTERVAL_MS=25
```

Payload tar/selective example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_payload_flow_plan.jmx \
  -JFLOW_MODE=tar-selective \
  -JTARGET_HOST=127.0.0.1 \
  -JTARGET_PORT=18084 \
  -JPACK_COUNT=5 \
  -JPACK_KB_PER_FILE=10 \
  -JSELECTIVE_COUNT=3
```

CRUD exact example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_crud_flow_plan.jmx \
  -JTARGET_HOST=127.0.0.1 \
  -JTARGET_PORT=18085 \
  -JITEM_NAME=smoke-item \
  -JITEM_VALUE=42
```

WebSocket example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_ws_flow_plan.jmx \
  -JFLOW_MODE=broadcast \
  -JTARGET_HOST=127.0.0.1 \
  -JTARGET_PORT=18088 \
  -JWS_ROOM=smoke-room \
  -JWS_MESSAGE=smoke-broadcast
```

Auth example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_auth_flow_plan.jmx \
  -JFLOW_MODE=session \
  -JDEMO_USERNAME=alice \
  -JDEMO_PASSWORD=demo-password \
  -JSESSION_USES=2
```

DB-heavy example:

```bash
jmeter -n \
  -t engines/jmeter/target_apps_db_flow_plan.jmx \
  -JFLOW_MODE=list-filter \
  -JDB_LIST_CATEGORY=sales \
  -JDB_LIST_STATUS=ready \
  -JDB_LIST_LIMIT=10
```

## Docker Example

```bash
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  --network host \
  justb4/jmeter:5.5 \
  -n \
  -t engines/jmeter/target_apps_sse_plan.jmx \
  -JSSE_ENDPOINT_PATH=/api/events \
  -JSSE_COUNT=5 \
  -JSSE_INTERVAL_MS=50
```

## Limitations

- JMeter coverage is currently selective correspondence coverage across the target catalog, not full profile-for-profile parity.
- The JSR223 plans are intended for bounded smoke and functional validation, not for high-scale engine benchmarking against k6.
- WebSocket, SSE, auth-heavy, and DB-heavy JMeter flows are demo-only and local-only; they must not be pointed at third-party systems.
