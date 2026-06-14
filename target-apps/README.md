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

Each app exposes `/health`, explicit safe limits, deterministic behavior where randomness exists, and a manifest in `target-apps/manifests/`.

## Local Run

```bash
docker compose -f target-apps/docker-compose.target-apps.yml up --build -d
docker compose -f target-apps/docker-compose.target-apps.yml ps
curl http://127.0.0.1:18080/health
curl "http://127.0.0.1:18081/api/delay/250"
curl "http://127.0.0.1:18082/api/flaky?rate=0.5&deterministic=true&request_key=ci"
curl "http://127.0.0.1:18084/api/download?kb=32"
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
```

## Notes

- Ports are bound to `127.0.0.1` only.
- The suite is intentionally capped to avoid overwhelming laptops or CI runners.
- `auth-flow-api` uses demo-only credentials: any username with password `demo-password`.

