# Target App Local Runbook

This runbook describes how to start, verify, and stop the diversified local target app suite under `target-apps/`.

## Purpose

Use this suite when you need local, reproducible HTTP targets for load-shape validation without depending on external services, secrets, or paid infrastructure.

## Prerequisites

- Docker Desktop or equivalent Docker Engine
- Local ports `18080` through `18086` available on `127.0.0.1`

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
curl -X POST http://127.0.0.1:18085/api/items -H "Content-Type: application/json" -d '{"name":"demo","value":1}'
curl -X POST http://127.0.0.1:18086/api/login -H "Content-Type: application/json" -d '{"username":"alice","password":"demo-password"}'
```

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
- `crud-api`: in-memory only
- `auth-flow-api`: demo-only credentials and bounded checkout quantity

If a request exceeds a safe limit, the app should return `422`.

## CI Notes

- CI does not need to boot the suite in Docker for basic validation.
- Metadata and endpoint behavior are covered by `pytest target-app/ target-apps/tests -v`.
- Template registry and manifest-driven task creation are covered by `python manage.py test apps/ --verbosity=2`.
- Existing Control Plane checks remain:
  - `python manage.py check`
  - `python manage.py test apps/ --verbosity=2`

## Troubleshooting

- If a port is already in use, stop the conflicting process or temporarily remap the port in `target-apps/docker-compose.target-apps.yml`.
- If health checks fail, inspect container logs with `docker compose -f target-apps/docker-compose.target-apps.yml logs <service>`.
- If CI-safe behavior becomes flaky, prefer deterministic mode instead of adding retries.
