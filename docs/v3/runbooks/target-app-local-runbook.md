# Target App Local Runbook

This runbook describes how to start, verify, and stop the diversified local target app suite under `target-apps/`.

## Purpose

Use this suite when you need local, reproducible HTTP targets for load-shape validation without depending on external services, secrets, or paid infrastructure.

## Prerequisites

- Docker Desktop or equivalent Docker Engine
- Local ports `18080` through `18089` available on `127.0.0.1`

The compose file keeps `18080-18089` as defaults, but each service port can be overridden with environment variables such as `ECHO_API_PORT`, `PAYLOAD_API_PORT`, and `DB_API_PORT`.

## Start The Suite

```bash
docker compose -f target-apps/docker-compose.target-apps.yml up --build -d
docker compose -f target-apps/docker-compose.target-apps.yml ps
```

Ports are bound to loopback only, so they are not exposed beyond the local host by default.

## Health Checks

```bash
curl http://127.0.0.1:18080/health
curl http://127.0.0.1:18081/health
curl http://127.0.0.1:18082/health
curl http://127.0.0.1:18083/health
curl http://127.0.0.1:18084/health
curl http://127.0.0.1:18085/health
curl http://127.0.0.1:18086/health
curl http://127.0.0.1:18087/health
curl http://127.0.0.1:18088/health
curl http://127.0.0.1:18089/health
```

Expected response shape:

```json
{"status":"ok","target_app_id":"echo-api"}
```

## Sample Requests

```bash
curl "http://127.0.0.1:18080/api/echo?message=hello&repeat=2"
curl "http://127.0.0.1:18081/api/delay/250"
curl "http://127.0.0.1:18082/api/flaky?rate=1&deterministic=true&request_key=ci"
curl "http://127.0.0.1:18083/api/cpu?iterations=250000"
curl "http://127.0.0.1:18084/api/download?kb=32"
curl http://127.0.0.1:18084/api/files/manifest?count=2\&kb_per_file=8
curl http://127.0.0.1:18084/api/files/fixture-pack?count=3\&kb_per_file=10
curl http://127.0.0.1:18084/api/files/fixture-1?kb=8 -o /tmp/fixture-1.bin
curl http://127.0.0.1:18084/api/files/archive?count=3\&kb_per_file=10 -o /tmp/fixture-pack.zip
curl http://127.0.0.1:18084/api/files/read-many?count=3\&kb_per_file=10
curl http://127.0.0.1:18084/api/files/tar-package?file_ids=fixture-1\&file_ids=fixture-3\&kb_per_file=10 -o /tmp/fixture-pack.tar
curl -X POST http://127.0.0.1:18084/api/files/selective-fetch -H "Content-Type: application/json" -d '{"file_ids":["fixture-1","fixture-3"],"kb_per_file":10}'
curl -X POST http://127.0.0.1:18085/api/items -H "Content-Type: application/json" -d '{"name":"demo","value":1}'
curl -X POST http://127.0.0.1:18086/api/login -H "Content-Type: application/json" -d '{"username":"alice","password":"demo-password"}'
curl -X POST http://127.0.0.1:18086/api/session/login -H "Content-Type: application/json" -d '{"username":"alice","password":"demo-password","session_uses":2}' -c /tmp/auth-cookies.txt
curl http://127.0.0.1:18086/api/session/profile -b /tmp/auth-cookies.txt
curl -N "http://127.0.0.1:18087/api/events?count=3&interval_ms=10"
curl -N "http://127.0.0.1:18087/api/progress-heavy?steps=6&interval_ms=10"
curl http://127.0.0.1:18089/api/records?category=sales&limit=5
```

## Docker Runtime Smoke Validation

Use the real runtime smoke script when you need build-and-run validation instead of only `docker compose ... config --quiet`:

```bash
bash target-apps/scripts/smoke_docker_target_apps.sh
```

The script:

- builds the shared image
- boots the compose stack
- retries `/health` checks with bounded waits
- calls one representative endpoint per target app
- exercises file-heavy and auth-heavy branches for `payload-api` and `auth-flow-api`
- includes a bounded in-container WebSocket runtime probe for `ws-api`
- dumps `docker compose ps` and logs on failure
- always runs cleanup on exit

By default the smoke script overrides the host port bindings to `18180-18189`, so it can run alongside a manually started local suite that still uses `18080-18089`.

## Manifest-Driven Task Creation

The Control Plane can now create tasks from local target templates without manually specifying `engine`, `script_path`, and `target_url`.

List templates:

```bash
curl http://127.0.0.1:9000/api/tasks/templates/ \
  -H "X-PLOADTESTING-API-TOKEN: ci-test-token"
```

Create a task from a template:

```bash
curl -X POST http://127.0.0.1:9000/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-PLOADTESTING-API-TOKEN: ci-test-token" \
  -d '{
    "target_app_id": "echo-api",
    "target_profile_id": "echo-k6-smoke",
    "created_by": "local-runbook"
  }'
```

## k6 SSE Sample Scenario

Finite SSE smoke validation is available through:

```bash
k6 run -e TARGET_URL=http://127.0.0.1:18087 engines/k6/target_apps_sse_smoke.js
```

Useful overrides:

```bash
k6 run \
  -e TARGET_URL=http://127.0.0.1:18087 \
  -e SSE_ENDPOINT_PATH=/api/ticker \
  -e SSE_COUNT=6 \
  -e SSE_INTERVAL_MS=75 \
  engines/k6/target_apps_sse_smoke.js
```

Progress-heavy SSE profile:

```bash
k6 run \
  -e TARGET_URL=http://127.0.0.1:18087 \
  -e SSE_ENDPOINT_PATH=/api/progress-heavy \
  -e SSE_STEPS=24 \
  -e SSE_INTERVAL_MS=25 \
  engines/k6/target_apps_sse_smoke.js
```

WebSocket smoke samples:

```bash
k6 run -e TARGET_URL=http://127.0.0.1:18088 engines/k6/target_apps_ws_echo_smoke.js
k6 run -e TARGET_URL=http://127.0.0.1:18088 engines/k6/target_apps_ws_broadcast_smoke.js
```

SQLite DB-heavy smoke samples:

```bash
k6 run -e TARGET_URL=http://127.0.0.1:18089 engines/k6/target_apps_db_crud_flow.js
k6 run -e TARGET_URL=http://127.0.0.1:18089 engines/k6/target_apps_db_list_filter.js
```

Payload file-heavy samples:

```bash
k6 run -e TARGET_URL=http://127.0.0.1:18084 engines/k6/target_apps_payload_file_flow.js
k6 run -e TARGET_URL=http://127.0.0.1:18084 -e FILE_UPLOAD_MODE=1 engines/k6/target_apps_payload_file_flow.js
k6 run -e TARGET_URL=http://127.0.0.1:18084 engines/k6/target_apps_payload_archive_flow.js
k6 run -e TARGET_URL=http://127.0.0.1:18084 engines/k6/target_apps_payload_tar_selective_flow.js
```

Auth-heavy refresh and failure samples:

```bash
k6 run -e TARGET_URL=http://127.0.0.1:18086 engines/k6/target_apps_auth_refresh_flow.js
k6 run -e TARGET_URL=http://127.0.0.1:18086 -e ASSERT_FAILURE_BRANCHES=1 engines/k6/target_apps_auth_refresh_flow.js
```

Auth-heavy session and MFA-like samples:

```bash
k6 run -e TARGET_URL=http://127.0.0.1:18086 -e FLOW_MODE=session engines/k6/target_apps_auth_session_mfa_flow.js
k6 run -e TARGET_URL=http://127.0.0.1:18086 -e FLOW_MODE=mfa -e MFA_CHANNEL=sms engines/k6/target_apps_auth_session_mfa_flow.js
```

JMeter sample coverage is now available across the current target catalog with exact reciprocal profile metadata for the current k6/JMeter task templates.

Representative JMeter samples:

```bash
jmeter -n -t engines/jmeter/target_apps_echo_latency_plan.jmx -JTARGET_HOST=127.0.0.1 -JTARGET_PORT=18082 -JTARGET_PATH=/api/flaky -JTARGET_METHOD=GET -JTARGET_QUERY='rate=0.5&deterministic=true&request_key=ci' -JEXPECTED_STATUS_PREFIX=5
jmeter -n -t engines/jmeter/target_apps_payload_flow_plan.jmx -JFLOW_MODE=tar-selective -JTARGET_HOST=127.0.0.1 -JTARGET_PORT=18084 -JPACK_COUNT=5 -JPACK_KB_PER_FILE=10 -JSELECTIVE_COUNT=3
jmeter -n -t engines/jmeter/target_apps_sse_plan.jmx -JSSE_ENDPOINT_PATH=/api/progress-heavy -JSSE_STEPS=24 -JSSE_INTERVAL_MS=25
jmeter -n -t engines/jmeter/target_apps_ws_flow_plan.jmx -JFLOW_MODE=echo -JTARGET_HOST=127.0.0.1 -JTARGET_PORT=18088 -JWS_PATH=/ws/echo -JWS_MESSAGE=smoke-echo
jmeter -n -t engines/jmeter/target_apps_auth_flow_plan.jmx -JFLOW_MODE=session -JDEMO_USERNAME=alice -JDEMO_PASSWORD=demo-password -JSESSION_USES=2
jmeter -n -t engines/jmeter/target_apps_db_flow_plan.jmx -JFLOW_MODE=list-filter -JDB_LIST_CATEGORY=sales -JDB_LIST_STATUS=ready -JDB_LIST_LIMIT=10
```

Notes:

- The current rule is target-family parity, not strict one-to-one parity for every profile.
- SSE and WebSocket JMeter plans use Groovy plus the Java 11 built-in clients instead of third-party protocol plugins.
- Worker-side JMeter execution now forwards template parameters as `-J...` properties, so manifest-driven tasks and direct CLI runs use the same property names.

Optional overrides are still allowed:

```bash
curl -X POST http://127.0.0.1:9000/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-PLOADTESTING-API-TOKEN: ci-test-token" \
  -d '{
    "target_app_id": "latency-api",
    "target_profile_id": "latency-k6-delay",
    "name": "latency-400ms",
    "target_url": "http://127.0.0.1:19081",
    "parameters": {
      "TARGET_URL": "http://127.0.0.1:19081",
      "DELAY_MS": "400"
    }
  }'
```

## Stop The Suite

```bash
docker compose -f target-apps/docker-compose.target-apps.yml down
```

## Safe Limits

- `latency-api`: max delay `5000ms`
- `error-api`: flaky rate limited to `0.0` through `1.0`
- `resource-api`: CPU `2,000,000` iterations, memory `64MB`, I-O `1024KB`
- `payload-api`: download `512KB`, upload `262144` bytes
- `payload-api`: file fixture `256KB`, file manifest count `20`, archive file count `10`, archive file size `64KB`, selective fetch count `8`, deterministic in-memory file bytes only
- `crud-api`: in-memory only
- `auth-flow-api`: demo-only credentials, checkout quantity `10`, access-token uses `5`, refresh uses `3`, session uses `5`, active MFA challenges `20`
- `sse-api`: `count <= 100`, `steps <= 100`, `progress-heavy steps <= 60`, `interval_ms <= 5000`, no infinite streaming
- `ws-api`: message size `1024` bytes, `10` messages per connection, `20` connections per process, room size `5`, idle timeout `5s`
- `db-api`: page size `50`, total rows `500`, deterministic SQLite seed rows, no external database dependency

If a request exceeds a safe limit, the app should return `422`.

## CI Notes

- CI does not need to boot the suite in Docker for basic validation.
- Manual CI can run the real Docker smoke validation job through `workflow_dispatch`.
- Metadata and endpoint behavior are covered by `pytest target-app/ target-apps/tests -v`.
- Template registry and manifest-driven task creation are covered by `python manage.py test apps/ --verbosity=2`.
- Existing Control Plane checks remain:
  - `python manage.py check`
  - `python manage.py test apps/ --verbosity=2`
- WebSocket representative runtime behavior is covered in the Docker smoke script instead of the always-on pytest path.
- File-heavy and auth-heavy representative flows are also covered in pytest and the Docker smoke script.
- Target template parity is also checked so every current target family exposes both `k6` and `jmeter` sample coverage.

## Troubleshooting

- If a port is already in use, either stop the conflicting process or override the affected host port with an environment variable such as `PAYLOAD_API_PORT=19084`.
- If health checks fail, inspect container logs with `docker compose -f target-apps/docker-compose.target-apps.yml logs <service>`.
- If CI-safe behavior becomes flaky, prefer deterministic mode instead of adding retries.
