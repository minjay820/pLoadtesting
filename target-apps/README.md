# pLoadtesting Target App Suite

This directory contains a diversified local target suite for pLoadtesting. These services exist only for authorized local development, CI validation, and controlled internal performance testing.

## Target Catalog

| Target App | Port | Coverage |
|---|---:|---|
| `echo-api` | `18080` | baseline / echo |
| `latency-api` | `18081` | latency / timeout |
| `error-api` | `18082` | error / flaky / 429 |
| `resource-api` | `18083` | CPU-bound / memory-bound / I-O-bound |
| `payload-api` | `18084` | payload size / upload / download / file-heavy / archive / read-many / tar / selective-fetch |
| `crud-api` | `18085` | CRUD / DB-like workload |
| `auth-flow-api` | `18086` | auth-like workload / auth-heavy refresh / expiry / session-cookie / MFA-demo |
| `sse-api` | `18087` | SSE / streaming / progress |
| `ws-api` | `18088` | WebSocket echo / broadcast |
| `db-api` | `18089` | SQLite DB-heavy / CRUD / list-filter |

Each app exposes `/health`, explicit safe limits, deterministic behavior where randomness exists, and a manifest in `target-apps/manifests/`.

Task templates live in `target-apps/task-templates/` and point to ready-to-use k6 or JMeter sample scenarios under `engines/`.
The current baseline is that every target family in this catalog has at least one `k6` sample and one `jmeter` sample.
Profile-level parity and remaining gaps are tracked in `docs/v3/domains/p-loadtesting-target-profile-coverage.md`.

Runtime smoke validation script:

```bash
bash target-apps/scripts/smoke_docker_target_apps.sh
```

The smoke script uses isolated localhost ports `18180-18189` by default so it can run even when the main local suite is already bound to `18080-18089`.

## Local Run

```bash
docker compose -f target-apps/docker-compose.target-apps.yml up --build -d
docker compose -f target-apps/docker-compose.target-apps.yml ps
curl http://127.0.0.1:18080/health
curl "http://127.0.0.1:18081/api/delay/250"
curl "http://127.0.0.1:18082/api/flaky?rate=0.5&deterministic=true&request_key=ci"
curl "http://127.0.0.1:18084/api/download?kb=32"
curl http://127.0.0.1:18084/api/files/manifest?count=2&kb_per_file=8
curl http://127.0.0.1:18084/api/files/fixture-pack?count=3&kb_per_file=10
curl http://127.0.0.1:18084/api/files/fixture-1?kb=8 -o /tmp/fixture-1.bin
curl http://127.0.0.1:18084/api/files/archive?count=3\&kb_per_file=10 -o /tmp/fixture-pack.zip
curl http://127.0.0.1:18084/api/files/read-many?count=3\&kb_per_file=10
curl http://127.0.0.1:18084/api/files/tar-package?file_ids=fixture-1\&file_ids=fixture-3\&kb_per_file=10 -o /tmp/fixture-pack.tar
curl -X POST http://127.0.0.1:18084/api/files/selective-fetch -H "Content-Type: application/json" -d '{"file_ids":["fixture-1","fixture-3"],"kb_per_file":10}'
curl -N "http://127.0.0.1:18087/api/progress-heavy?steps=6&interval_ms=10"
curl http://127.0.0.1:18089/api/records?category=sales&limit=5
docker compose -f target-apps/docker-compose.target-apps.yml down
```

Host ports can be overridden per service without editing the compose file, for example:

```bash
ECHO_API_PORT=19080 PAYLOAD_API_PORT=19084 docker compose -f target-apps/docker-compose.target-apps.yml up -d
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
- Default ports are `18080-18089`, but each service port can be overridden with environment variables such as `ECHO_API_PORT`, `PAYLOAD_API_PORT`, and `DB_API_PORT`.
- The suite is intentionally capped to avoid overwhelming laptops or CI runners.
- `auth-flow-api` uses demo-only credentials: any username with password `demo-password`.
- Manifest-driven Control Plane task creation can use `target_app_id` plus `target_profile_id`, for example `echo-api` + `echo-k6-smoke`.
- `sse-api` returns finite `text/event-stream` responses only; it never runs infinite streams.
- `sse-api` includes a bounded `progress-heavy` profile for denser step metadata without unbounded stream size.
- `ws-api` exposes bounded `WS /ws/echo` and `WS /ws/broadcast/{room}` flows only.
- `db-api` uses disposable SQLite state inside the app container and auto-seeds a small deterministic dataset.
- `payload-api` now includes bounded file-like manifest, binary download, and binary upload endpoints for file-heavy smoke paths.
- `payload-api` also includes bounded fixture-pack metadata, zip archive, and read-many summary endpoints for archive-style file-heavy coverage.
- `payload-api` now also includes bounded tar-like multi-file packaging and manifest-driven selective fetch coverage.
- `auth-flow-api` now includes bounded refresh, expiry, invalid-credential, and logout branches without any real identity provider or secret.
- `auth-flow-api` also includes demo-only cookie/session and MFA-like challenge/verify branches with deterministic behavior.
- JMeter coverage now includes selective target-family correspondence for `error-api`, `resource-api`, `payload-api`, `auth-flow-api`, `sse-api`, `ws-api`, and `db-api`.
