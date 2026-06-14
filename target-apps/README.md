# pLoadtesting Target App Suite

This directory contains a diversified local target suite for pLoadtesting. These services exist only for authorized local development, CI validation, and controlled internal performance testing.

## Target Catalog

| Target App | Port | Coverage |
|---|---:|---|
| `echo-api` | `18080` | baseline / echo |
| `latency-api` | `18081` | latency / timeout |
| `error-api` | `18082` | error / flaky / 429 |
| `resource-api` | `18083` | CPU-bound / memory-bound / I-O-bound |
| `payload-api` | `18084` | payload size / upload / download |
| `crud-api` | `18085` | CRUD / DB-like workload |
| `auth-flow-api` | `18086` | auth-like workload / scenario-style business flow |
| `sse-api` | `18087` | SSE / streaming / progress |
| `ws-api` | `18088` | WebSocket echo / broadcast |
| `db-api` | `18089` | SQLite DB-heavy / CRUD / list-filter |

Each app exposes `/health`, explicit safe limits, deterministic behavior where randomness exists, and a manifest in `target-apps/manifests/`.

Task templates live in `target-apps/task-templates/` and point to ready-to-use k6 or JMeter sample scenarios under `engines/`.

Runtime smoke validation script:

```bash
bash target-apps/scripts/smoke_docker_target_apps.sh
```

## Local Run

```bash
docker compose -f target-apps/docker-compose.target-apps.yml up --build -d
docker compose -f target-apps/docker-compose.target-apps.yml ps
curl http://127.0.0.1:18080/health
curl "http://127.0.0.1:18081/api/delay/250"
curl "http://127.0.0.1:18082/api/flaky?rate=0.5&deterministic=true&request_key=ci"
curl "http://127.0.0.1:18084/api/download?kb=32"
curl -N "http://127.0.0.1:18087/api/progress-heavy?steps=6&interval_ms=10"
curl http://127.0.0.1:18089/api/records?category=sales&limit=5
docker compose -f target-apps/docker-compose.target-apps.yml down
```

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

## Notes

- Ports are bound to `127.0.0.1` only.
- The suite is intentionally capped to avoid overwhelming laptops or CI runners.
- `auth-flow-api` uses demo-only credentials: any username with password `demo-password`.
- Manifest-driven Control Plane task creation can use `target_app_id` plus `target_profile_id`, for example `echo-api` + `echo-k6-smoke`.
- `sse-api` returns finite `text/event-stream` responses only; it never runs infinite streams.
- `sse-api` includes a bounded `progress-heavy` profile for denser step metadata without unbounded stream size.
- `ws-api` exposes bounded `WS /ws/echo` and `WS /ws/broadcast/{room}` flows only.
- `db-api` uses disposable SQLite state inside the app container and auto-seeds a small deterministic dataset.
