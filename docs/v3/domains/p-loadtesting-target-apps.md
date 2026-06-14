# pLoadtesting Target App Suite

This document defines the diversified local target app suite used by pLoadtesting for repeatable, authorized load-generation scenarios.

## Why A Diversified Target Suite Is Needed

The original repository shipped one reference FastAPI target with a small set of endpoints. That was enough for early smoke validation, but it does not cover the wider shapes a load-testing platform must exercise:

- baseline and echo behavior
- deterministic latency and timeout-style responses
- status-code, flaky, and 429 handling
- upload and download payload size stress
- CPU, memory, and disk I/O pressure
- CRUD and DB-like request patterns
- auth-like session handling
- scenario-style business flows

The `target-apps/` suite addresses that gap without changing the core Control Plane or Worker contracts.

## Scope And Safety

- These targets are only for local development, CI, and controlled internal testing.
- They must never be used to attack, probe, or relay traffic to third-party systems.
- Each target exposes `/health`.
- Every target has explicit safe limits to avoid overwhelming laptops or CI runners.
- Where randomness exists, deterministic mode is available so CI can replay the same behavior.

## Target App Catalog

| Target App | Base URL | Main Scenarios | Notes |
|---|---|---|---|
| `echo-api` | `http://127.0.0.1:18080` | baseline / echo | Good for smoke checks and low-cost response validation |
| `latency-api` | `http://127.0.0.1:18081` | latency / timeout | Caps delay at 5 seconds and converts timeout simulation into explicit 504 responses |
| `error-api` | `http://127.0.0.1:18082` | error / flaky / 429 | Supports deterministic flaky mode for CI |
| `resource-api` | `http://127.0.0.1:18083` | CPU-bound / memory-bound / I-O-bound | Uses bounded synthetic work only |
| `payload-api` | `http://127.0.0.1:18084` | payload size / upload / download | Uses deterministic filler payloads instead of external files |
| `crud-api` | `http://127.0.0.1:18085` | CRUD / DB-like workload | Uses in-memory state for low-cost reproducibility |
| `auth-flow-api` | `http://127.0.0.1:18086` | auth-like / scenario-style business flow | Demo-only bearer token workflow |

## Endpoint Groups

### echo-api

- `GET /health`
- `GET /api/echo`
- `POST /api/echo`

### latency-api

- `GET /health`
- `GET /api/delay/{ms}`
- `GET /api/timeout-simulation?ms=...`

### error-api

- `GET /health`
- `GET /api/status/{code}`
- `GET /api/flaky?rate=...&deterministic=true&request_key=...`
- `GET /api/rate-limit`

### resource-api

- `GET /health`
- `GET /api/cpu?iterations=...`
- `GET /api/memory?mb=...`
- `GET /api/io?kb=...`

### payload-api

- `GET /health`
- `GET /api/download?kb=...`
- `POST /api/upload`

### crud-api

- `GET /health`
- `GET /api/items`
- `POST /api/items`
- `GET /api/items/{id}`

### auth-flow-api

- `GET /health`
- `POST /api/login`
- `GET /api/profile`
- `POST /api/checkout`
- `GET /api/orders/{id}`

## Manifests

Each target app has a manifest under `target-apps/manifests/` with these fields:

- `target_app_id`
- `display_name`
- `runtime`
- `protocol`
- `base_url`
- `workload_types`
- `endpoints`
- `safe_limits`
- `default_profile`
- `notes`

These manifests are intended to be machine-readable metadata for future target selection, task templating, and validation automation.

## CI Validation Approach

Current CI coverage for the suite is intentionally minimal and stable:

- parse every manifest as structured metadata
- import every FastAPI app and verify `/health`
- verify safe-limit enforcement on delay, error, payload, and resource endpoints
- verify README commands and compose service definitions stay aligned
- keep existing Django `manage.py check` and `manage.py test apps/ --verbosity=2` unchanged

## Future Extensions

Future work may add:

- WebSocket targets
- gRPC targets
- SSE targets
- DB-heavy targets backed by disposable SQLite or Postgres containers
- file-heavy targets with bounded fixture sets
- auth-heavy targets with token refresh, session expiry, and policy branches

