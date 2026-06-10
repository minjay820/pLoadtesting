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

---

## 🧵 Script Specifications

| Script | Endpoint | VUs | Mode | Thresholds |
|---|---|:---:|---|---|
| `smoke.js` | `GET /api/health` | 1 | 10s run | p(99) < 500ms, Errors = 0% |
| `stress_cpu.js` | `GET /api/cpu-bound?n=1000000` | 0→50→0 | 30s ramp + 60s sustain + 10s down | p(95) < 2000ms, Errors < 5% |
| `stress_io.js` | `GET /api/io-bound?delay=1.0` | 200 | 200 VUs direct, 60s sustain | p(95) < 3500ms, Errors < 1% |
| `stress_data.js` | `POST /api/data` | 0→20 | 10s ramp + 60s sustain | p(95) < 1500ms, count = 100 |

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

---

### 5. Overriding VUs and Duration from CLI

```bash
# Override smoke VUs
k6 run --vus 5 --duration 30s smoke.js

# Override stages in stress test (k6 0.43+)
k6 run --stage 10s:10,30s:10,10s:0 stress_cpu.js
```

---

### 6. Executing via Docker

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
