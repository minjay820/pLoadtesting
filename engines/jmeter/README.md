# ⚙️ engines/jmeter — JMeter Testing Engine

This directory contains the Apache JMeter test plan configurations for `pLoadtesting`, corresponding to the four endpoints of the Target App: health checks, CPU stress, I/O stress, and data serialization.

---

## 📁 Directory Structure

```
engines/jmeter/
├── ploadtesting_test_plan.jmx   ← Main test plan (JMeter 5.5+ compatible)
├── reports/                     ← Automatically generated (ignored by git)
│   ├── results.jtl              ←   Raw CSV-formatted metrics
│   └── html/                    ←   HTML visual report dashboard
└── README.md                    ← This file
```

---

## 🧵 Thread Group Specifications

| # | Name | Endpoint | Threads | Ramp-up | Duration / Loop |
|:---:|---|---|:---:|:---:|:---:|
| TG1 | Smoke Test | `GET /api/health` | 1 | 1s | Loop × 5 |
| TG2 | CPU Stress | `GET /api/cpu-bound?n=1000000` | 50 | 30s | 60s |
| TG3 | I/O Stress | `GET /api/io-bound?delay=1.0` | 200 | 5s | 60s |
| TG4 | Data API | `POST /api/data` | 20 | 10s | 60s |

---

## 🚀 Execution Guide

### Prerequisites

| Tool | Version Requirement | Download |
|---|---|---|
| Apache JMeter | 5.5+ | https://jmeter.apache.org/download_jmeter.cgi |
| Java | 11+ | https://adoptium.net |

```bash
# Verify JMeter CLI is available
jmeter --version
```

---

### 1. Standard CLI Non-GUI Execution (Recommended)

> **Important**: Always use Non-GUI mode for official load tests. The JMeter GUI consumes additional resources, distorting test results.

```bash
# Navigate to this directory
cd engines/jmeter

# Create reports directories
mkdir -p reports/html

# Run the test plan to generate both JTL and HTML reports
jmeter \
  -n \
  -t ploadtesting_test_plan.jmx \
  -l reports/results.jtl \
  -e \
  -o reports/html
```

**Parameters Reference**

| Flag | Description |
|---|---|
| `-n` | Non-GUI CLI mode (Required) |
| `-t <file>` | Path to `.jmx` test plan |
| `-l <file>` | Destination file for raw output JTL logs |
| `-e` | Generate HTML dashboard reports on completion |
| `-o <dir>` | Destination directory for HTML reports (must be empty or non-existent) |

After completion, view the reports in your browser:

```bash
open reports/html/index.html   # macOS
xdg-open reports/html/index.html   # Linux
```

---

### 2. Overriding Target Host and Port (CLI Parameter Injection)

The test plan defaults targets to `localhost:8000`. You can override targets using `-J` variables:

```bash
jmeter -n \
  -t ploadtesting_test_plan.jmx \
  -l reports/results.jtl \
  -e -o reports/html \
  -JTARGET_HOST=192.168.1.100 \
  -JTARGET_PORT=8000
```

---

### 3. Run a Single Thread Group

You can disable groups in the JMeter GUI (Right-click -> Disable), save, and run via the CLI.
Alternatively, use dedicated configurations:

```bash
# Example: Run smoke test only (disable TG2-TG4 in GUI first)
jmeter -n -t ploadtesting_test_plan_smoke_only.jmx -l reports/smoke.jtl
```

---

### 4. Running via Docker

```bash
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  --network host \
  justb4/jmeter:5.5 \
  -n \
  -t ploadtesting_test_plan.jmx \
  -l reports/results.jtl \
  -e -o reports/html
```

---

### 5. Generate HTML Dashboard from Existing JTL Logs

```bash
jmeter -g reports/results.jtl -o reports/html_regenerated
```

---

## 📊 Key HTML Dashboard Metrics

| Metric | Description | Health Benchmark (Reference) |
|---|---|---|
| **Throughput** | Requests per second (RPS) completed | Higher is better |
| **Average** | Mean response time (ms) | `< 500ms` (depending on SLA) |
| **90th pct** | Response time for 90% of requests | `< 1000ms` |
| **99th pct** | Response time for 99% of requests | `< 3000ms` |
| **Error %** | Percentage of failed HTTP requests | `< 1%` |
| **Received KB/s** | Network download throughput | Depends on TG4 data size |

---

## 🔧 Troubleshooting

### Q1: `Error in NonGUIDriver java.lang.Exception: Could not open JTL file`
* **Reason**: The `reports/` folder does not exist.
* **Solution**: Create it by running `mkdir -p reports/html` first.

### Q2: `An error occurred: Non empty output folder reports/html`
* **Reason**: The `-o` output directory already contains files.
* **Solution**: Clear it with `rm -rf reports/html` first.

### Q3: TG3 I/O stress active threads do not reach 200
* **Reason**: Fast timeout collisions.
* **Solution**: Check or adjust `HTTPSampler.response_timeout` properties.
