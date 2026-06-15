# ⚙️ engines/k6 — k6 Load Testing Engine

This directory contains the [k6](https://k6.io) load testing scripts for `pLoadtesting`. Written in JavaScript (ES2015+), these scripts map directly to the four endpoints of the Target App.

---

## 📁 Directory Structure

```
engines/k6/
├── smoke.js          ← Smoke verification (GET /api/health)
├── stress_cpu.js     ← CPU stress run (GET /api/cpu-bound)
├── stress_io.js      ← Async I/O stress run (GET /api/io-bound)
├── stress_data.js    ← JSON serialization stress run (POST /api/data)
├── results/          ← Test output summaries (ignored by git)
│   ├── smoke.json
│   ├── stress_cpu.json
│   ├── stress_io.json
│   └── stress_data.json
└── README.md         ← This file
```

Profile-level k6↔JMeter parity is tracked in `docs/v3/domains/p-loadtesting-target-profile-coverage.md`.

---

## 🧵 Script Specifications

| Script | Endpoint | VUs | Mode | Thresholds |
|---|---|:---:|---|---|
| `smoke.js` | `GET /api/health` | 1 | 10s run | p(99) < 500ms, Errors = 0% |
| `stress_cpu.js` | `GET /api/cpu-bound?n=1000000` | 0→50→0 | 30s ramp + 60s sustain + 10s down | p(95) < 2000ms, Errors < 5% |
| `stress_io.js` | `GET /api/io-bound?delay=1.0` | 200 | 200 VUs direct, 60s sustain | p(95) < 3500ms, Errors < 1% |
| `stress_data.js` | `POST /api/data` | 0→20 | 10s ramp + 60s sustain | p(95) < 1500ms, count = 100 |
| `target_apps_echo_smoke.js` | `GET /api/echo` | 1 | 10s run | Smoke for `echo-api` |
| `target_apps_latency_delay.js` | `GET /api/delay/{ms}` | 0→10 | 30s total | Delay profile for `latency-api` |
| `target_apps_error_flaky.js` | `GET /api/flaky` | 5 | 15s run | Deterministic flaky checks |
| `target_apps_resource_cpu.js` | `GET /api/cpu` | 0→10 | 30s total | Bounded CPU profile |
| `target_apps_crud_flow.js` | `POST /api/items` + `GET /api/items/{id}` | 5 | 20s run | CRUD flow sample |
| `target_apps_auth_checkout.js` | login/profile/checkout | 5 | 20s run | Auth-style business flow sample |
| `target_apps_auth_refresh_flow.js` | login/expiry/refresh/logout | 3 | 4 iterations | Auth-heavy refresh and failure branches |
| `target_apps_auth_session_mfa_flow.js` | session-cookie or MFA demo flow | 3 | 4 iterations | Cookie/session and deterministic MFA-like auth flow |
| `target_apps_sse_smoke.js` | finite SSE stream | 1 | 3 iterations | SSE streaming smoke for `sse-api` |
| `target_apps_payload_download.js` | `GET /api/download` | 2 | 10s run | Bounded text payload download |
| `target_apps_payload_file_flow.js` | file manifest/download/upload | 3 | 4 iterations | File-heavy bounded payload flow |
| `target_apps_payload_archive_flow.js` | fixture-pack/archive/read-many | 3 | 4 iterations | Archive-style file-heavy flow |
| `target_apps_payload_tar_selective_flow.js` | manifest/selective-fetch/tar-package | 2 | 4 iterations | Tar-like package and selective fetch flow |
| `target_apps_ws_echo_smoke.js` | `WS /ws/echo` | 1 | 2 iterations | Bounded WebSocket echo smoke |
| `target_apps_ws_broadcast_smoke.js` | `WS /ws/broadcast/{room}` | 1 | 2 iterations | Bounded WebSocket broadcast smoke |
| `target_apps_db_crud_flow.js` | `POST/GET /api/records` | 2 | 4 iterations | SQLite CRUD smoke |
| `target_apps_db_list_filter.js` | `GET /api/records` | 2 | 4 iterations | SQLite list/filter smoke |

---

## 🚀 Prerequisites

```bash
# Install on macOS (Homebrew)
brew install k6

# Verify version (requires 0.45+)
k6 version
```

For other OS installation options, please refer to the [k6 Installation Guide](https://k6.io/docs/get-started/installation/).

---

## ▶️ Execution Guide

### 1. Standard Runs (targeting local Target App)

```bash
# Navigate to this directory
cd engines/k6

# Run Smoke check
k6 run smoke.js

# Run CPU Stress
k6 run stress_cpu.js

# Run I/O Stress
k6 run stress_io.js

# Run Data Serialization Stress
k6 run stress_data.js

# Run SSE Smoke
k6 run -e TARGET_URL=http://127.0.0.1:18087 target_apps_sse_smoke.js

# Run payload text download
k6 run -e TARGET_URL=http://127.0.0.1:18084 target_apps_payload_download.js

# Run payload file flow
k6 run -e TARGET_URL=http://127.0.0.1:18084 target_apps_payload_file_flow.js

# Run payload archive flow
k6 run -e TARGET_URL=http://127.0.0.1:18084 target_apps_payload_archive_flow.js

# Run payload tar selective flow
k6 run -e TARGET_URL=http://127.0.0.1:18084 target_apps_payload_tar_selective_flow.js

# Run auth refresh flow
k6 run -e TARGET_URL=http://127.0.0.1:18086 target_apps_auth_refresh_flow.js

# Run auth session flow
k6 run -e TARGET_URL=http://127.0.0.1:18086 -e FLOW_MODE=session target_apps_auth_session_mfa_flow.js

# Run auth MFA flow
k6 run -e TARGET_URL=http://127.0.0.1:18086 -e FLOW_MODE=mfa -e MFA_CHANNEL=sms target_apps_auth_session_mfa_flow.js

# Run SSE progress-heavy
k6 run \
  -e TARGET_URL=http://127.0.0.1:18087 \
  -e SSE_ENDPOINT_PATH=/api/progress-heavy \
  -e SSE_STEPS=24 \
  -e SSE_INTERVAL_MS=25 \
  target_apps_sse_smoke.js

# Run WebSocket echo smoke
k6 run -e TARGET_URL=http://127.0.0.1:18088 target_apps_ws_echo_smoke.js

# Run WebSocket broadcast smoke
k6 run -e TARGET_URL=http://127.0.0.1:18088 target_apps_ws_broadcast_smoke.js

# Run SQLite CRUD smoke
k6 run -e TARGET_URL=http://127.0.0.1:18089 target_apps_db_crud_flow.js

# Run SQLite list/filter smoke
k6 run -e TARGET_URL=http://127.0.0.1:18089 target_apps_db_list_filter.js
```

---

### 2. Outputting JSON Results

The `--out json` argument tells k6 to save metrics to a local file, which worker agents can parse:

```bash
# Create target folder
mkdir -p results

# Execute and write outputs
k6 run smoke.js       --out json=results/smoke.json
k6 run stress_cpu.js  --out json=results/stress_cpu.json
k6 run stress_io.js   --out json=results/stress_io.json
k6 run stress_data.js --out json=results/stress_data.json
```

**JSON Output Format**: Each line represents a separate metrics snapshot (JSON Lines format), allowing streams to be read asynchronously:

```jsonl
{"type":"Metric","data":{"name":"http_req_duration","type":"trend","contains":"time",...}}
{"type":"Point","data":{"metric":"http_req_duration","time":"...","value":142.5,...}}
```

---

### 3. Outputting to Multiple Formats

```bash
k6 run stress_cpu.js \
  --out json=results/stress_cpu.json \
  --out csv=results/stress_cpu.csv
```

---

### 4. Overriding Target Host (Environment Variable Injection)

All scripts read the `TARGET_URL` environment variable (defaults to `http://localhost:8000`):

```bash
# Run against a remote server
k6 run -e TARGET_URL=http://192.168.1.100:8000 stress_cpu.js

# Combined execution
k6 run \
  -e TARGET_URL=http://staging.example.com:8000 \
  --out json=results/stress_cpu.json \
  stress_cpu.js
```

WebSocket scripts derive `ws://` from `TARGET_URL` automatically, so the same `TARGET_URL=http://127.0.0.1:18088` convention still applies.

`target_apps_payload_file_flow.js` supports `FILE_UPLOAD_MODE=1` for roundtrip upload checks.
`target_apps_auth_refresh_flow.js` supports `ASSERT_FAILURE_BRANCHES=1` to include invalid-credential and revoked-token assertions.
`target_apps_auth_session_mfa_flow.js` supports `FLOW_MODE=session|mfa` and `MFA_ISSUE_MODE=bearer|session`.

---

### 5. Duration-Based Execution Metadata

The worker passes Phase 5.8 execution metadata to representative k6 scripts through environment variables:

- `DURATION_SECONDS`
- `RAMP_UP_SECONDS`
- `RAMP_DOWN_SECONDS`
- `GRACEFUL_STOP_SECONDS`
- `ITERATION_LIMIT`
- `STOP_POLICY`
- `DATA_POLICY`

The helper at `engines/k6/lib/execution.js` builds k6 `options` from these values. Current helper coverage is intentionally limited to:

- `target_apps_payload_download.js`
- `target_apps_echo_smoke.js`
- `target_apps_latency_delay.js`
- `target_apps_auth_checkout.js`

Other k6 scripts continue using their existing hard-coded options until follow-up coverage expands.

Phase 5.9 also lets a worker pass one manual shard dataset assignment to k6 through environment variables:

- `SHARD_ID`
- `DATASET_SOURCE`
- `DATASET_FORMAT`
- `DATASET_OFFSET`
- `DATASET_LIMIT`

These variables are metadata only. The current k6 scripts do not automatically load `artifact://` or `inline://` datasets; script-specific dataset consumption remains future work.

Example:

```bash
k6 run \
  -e TARGET_URL=http://127.0.0.1:18084 \
  -e DURATION_SECONDS=600 \
  -e RAMP_UP_SECONDS=30 \
  -e RAMP_DOWN_SECONDS=30 \
  -e GRACEFUL_STOP_SECONDS=30 \
  -e DATA_POLICY=duration_first \
  target_apps_payload_download.js
```

Shard metadata example:

```bash
k6 run \
  -e TARGET_URL=http://127.0.0.1:18084 \
  -e SHARD_ID=users-a \
  -e DATASET_SOURCE=artifact://datasets/users.csv \
  -e DATASET_FORMAT=csv \
  -e DATASET_OFFSET=0 \
  -e DATASET_LIMIT=2000 \
  target_apps_payload_download.js
```

---

### 6. Overriding VUs and Duration from CLI

```bash
# Override smoke VUs
k6 run --vus 5 --duration 30s smoke.js

# Override stages in stress test (k6 0.43+)
k6 run --stage 10s:10,30s:10,10s:0 stress_cpu.js
```

---

### 7. Executing via Docker

```bash
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  --network host \
  grafana/k6 run smoke.js
```

---

## 📊 Core Metrics Reference

| Metric Name | Description |
|---|---|
| `http_req_duration` | End-to-end HTTP request duration (DNS + TCP connect + processing + transfer) |
| `http_req_failed` | Percentage of failed HTTP requests (4xx/5xx responses) |
| `http_reqs` | Total HTTP request counter and calculated RPS |
| `vus` | Active Virtual Users |
| `cpu_server_elapsed_ms` | Server-side calculation duration (for CPU tests) |
| `data_item_count` | Number of items returned in the response array |

---

## 🔧 Exit Codes and Failures

If any specified threshold fails, k6 exits with **exit code 99**, allowing pipelines to fail automatically:

```bash
k6 run stress_cpu.js --out json=results/stress_cpu.json
if [ $? -ne 0 ]; then
  echo "❌ Threshold failed, test aborted"
  exit 1
fi
echo "✅ All thresholds passed successfully"
```
