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
- finite streaming via Server-Sent Events
- bounded WebSocket connection-lifecycle validation
- SQLite-backed DB-heavy CRUD and list/filter validation

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
| `sse-api` | `http://127.0.0.1:18087` | SSE / streaming / progress | Finite `text/event-stream` responses only, including progress-heavy profile |
| `ws-api` | `http://127.0.0.1:18088` | WebSocket echo / broadcast | Strict caps on connections, room size, message size, and per-connection messages |
| `db-api` | `http://127.0.0.1:18089` | DB-heavy / CRUD / list-filter | SQLite-backed disposable dataset with deterministic seed rows |

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

### sse-api

- `GET /health`
- `GET /api/events?count=...&interval_ms=...`
- `GET /api/ticker?count=...&interval_ms=...`
- `GET /api/progress?steps=...&interval_ms=...`
- `GET /api/progress-heavy?steps=...&interval_ms=...`

### ws-api

- `GET /health`
- `WS /ws/echo`
- `WS /ws/broadcast/{room}`

### db-api

- `GET /health`
- `POST /api/records`
- `GET /api/records`
- `GET /api/records/{id}`
- `PATCH /api/records/{id}`

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

## Task Templates And Sample Scenarios

The suite now includes task templates under `target-apps/task-templates/` and engine samples under `engines/k6/` plus `engines/jmeter/`.

Template flow:

1. `target_app_id` selects the target family.
2. `target_profile_id` selects a ready-made scenario profile.
3. The Control Plane resolves that profile into the existing task fields:
   - `engine`
   - `script_path`
   - `target_url`
   - `parameters`

Examples:

| Target App | Profile | Engine | Purpose |
|---|---|---|---|
| `echo-api` | `echo-k6-smoke` | k6 | basic smoke and response validation |
| `latency-api` | `latency-k6-delay` | k6 | reproducible delay behavior |
| `error-api` | `error-k6-flaky` | k6 | deterministic flaky response validation |
| `resource-api` | `resource-k6-cpu` | k6 | bounded CPU workload |
| `payload-api` | `payload-jmeter-download` | JMeter | payload download throughput |
| `crud-api` | `crud-k6-flow` | k6 | create-and-fetch flow |
| `auth-flow-api` | `auth-k6-checkout` | k6 | login and checkout business flow |
| `sse-api` | `sse-k6-smoke` | k6 | bounded SSE smoke stream |
| `sse-api` | `sse-k6-ticker` | k6 | bounded SSE ticker stream |
| `sse-api` | `sse-k6-progress-heavy` | k6 | richer bounded progress stream |
| `ws-api` | `ws-k6-echo-smoke` | k6 | bounded WebSocket echo smoke |
| `ws-api` | `ws-k6-broadcast-smoke` | k6 | bounded WebSocket broadcast smoke |
| `db-api` | `db-k6-crud-smoke` | k6 | SQLite-backed CRUD smoke |
| `db-api` | `db-k6-list-filter` | k6 | SQLite-backed list/filter smoke |

This keeps the Worker and task model unchanged while allowing manifest-driven selection.

## CI Validation Approach

Current CI coverage for the suite is intentionally minimal and stable:

- parse every manifest as structured metadata
- import every FastAPI app and verify `/health`
- verify safe-limit enforcement on delay, error, payload, and resource endpoints
- verify README commands and compose service definitions stay aligned
- keep existing Django `manage.py check` and `manage.py test apps/ --verbosity=2` unchanged

The suite also now has a real runtime smoke path:

- `bash target-apps/scripts/smoke_docker_target_apps.sh`
- build the shared image
- start the full compose stack
- wait and retry `/health`
- probe a representative endpoint per service
- dump `docker compose ps` and logs on failure
- always clean up containers on exit

This is exposed as a manual GitHub Actions run rather than a per-push job so CI time stays bounded.

## SSE Safety Limits

The first streaming target intentionally stays narrow:

- `count <= 100`
- `steps <= 100`
- `progress-heavy steps <= 60`
- `interval_ms <= 5000`
- default stream sizes stay small
- no infinite streams
- deterministic mode is on by default for CI-friendly replay

## WebSocket Safety Limits

- `max_message_size_bytes = 1024`
- `max_messages_per_connection = 10`
- `max_concurrent_connections = 20`
- `max_room_size = 5`
- `idle_timeout_seconds = 5`
- echo and broadcast paths both hard-close after bounded message counts

## SQLite DB-Heavy Safety Limits

- `limit <= 50`
- `offset <= 500`
- total row cap `<= 500`
- bounded text field lengths
- deterministic startup seed rows only
- no external database service, no cross-run persistence requirement

## Future Extensions

Future work may add the following, with the current evaluation posture:

| Extension | Current Assessment | Recommended Next Step |
|---|---|---|
| WebSocket | Implemented as a bounded echo/broadcast target with manual Docker smoke validation | Expand only after current caps remain stable under local and CI usage |
| gRPC | Useful for protocol coverage, but adds tooling/runtime complexity to CI | Defer until there is a real gRPC consumer requirement |
| SSE | Implemented first because it is finite, HTTP-native, and cheap to validate | Expand through richer bounded profiles such as progress-heavy before larger payload experiments |
| DB-heavy | Implemented with SQLite-backed bounded write/read and list/filter coverage | Revisit heavier joins, seed control, or file-backed artifacts only if current target proves insufficient |
| file-heavy | Valuable for upload/download and local artifact churn | Add bounded fixture packs and strict size caps |
| auth-heavy | Valuable, but easy to drift into secret-like behavior | Extend demo-only auth-flow with refresh/expiry branches, still no real secrets |

gRPC remains deferred because it would add additional protocol tooling and CI surface area without an immediate repo-driven use case. File-heavy and deeper auth-heavy targets remain deferred until the new WebSocket and SQLite targets prove stable.
