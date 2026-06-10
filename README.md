# 🌌 pLoadtesting

> **Multi-engine automated load testing ecosystem for k6, JMeter, worker agents, control plane orchestration, and reproducible performance reports.**

[![Phase](https://img.shields.io/badge/Phase-0%20Scaffolding-blueviolet)]()
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

> [!WARNING]
> **Safety & Production Readiness Warnings:**
> * This project is an early-stage preview.
> * Use this project **only** for authorized performance testing against systems you own or have explicit permission to test.
> * Do not test systems you do not own or do not have explicit permission to test.
> * **Do not expose** Control Plane or Worker endpoints to the public internet without authentication, authorization, network isolation, and rate limiting.
> * The Control Plane and Worker Agent components are **not production-ready yet**.

---

## 📐 Architecture Blueprint

```
                          ┌─────────────────────────────────────────┐
                          │           Control Plane (Web UI)         │
                          │  ┌──────────────┐  ┌──────────────────┐ │
                          │  │  Task Queue  │  │  Report Collector│ │
                          │  └──────┬───────┘  └────────┬─────────┘ │
                          └─────────┼────────────────────┼───────────┘
                                    │  dispatch           │  results
                    ┌──────────────┼──────────────────────┼────────────────┐
                    ▼              ▼                       ▼                ▼
              ┌──────────┐  ┌──────────┐           ┌──────────┐    ┌──────────┐
              │ Worker 1 │  │ Worker 2 │    ...     │ Worker N │    │  Worker  │
              │  (k6)    │  │(JMeter)  │            │ (Future) │    │ (custom) │
              └────┬─────┘  └────┬─────┘           └────┬─────┘    └────┬─────┘
                   │              │                       │               │
                   └──────────────┴───────────────────────┴───────────────┘
                                             │
                                    HTTP / gRPC / WS
                                             │
                              ┌──────────────▼──────────────┐
                              │         Target App           │
                              │    (Reference API Server)    │
                              └─────────────────────────────┘
```

---

## 🗂️ Directory Structure

```
pLoadtesting/
│
├── target-app/               # Reference API server used as a load testing target
├── engines/                  # Load testing scripts and scenario assets
│   ├── k6/                   # k6 test scripts
│   ├── jmeter/               # JMeter test plans
│   └── loadrunner/           # Optional future enterprise engine adapter
│
├── control-plane/            # Planned orchestration API and web console
├── workers/                  # Planned remote execution agents
├── docker-compose.yml        # Container orchestration configuration
└── README.md                 # This file
```

---

### 📦 target-app/

**Purpose**: A standardized, deployable reference target API service used as the payload destination for all test engines.

| Item | Details |
|---|---|
| Tech Stack | **Python 3.11 + FastAPI + Uvicorn (uvloop)** |
| Deployment | Dockerized, launch via `docker compose up target-app` (Port 8000) |
| Interactive Spec | Swagger UI available at `http://localhost:8000/docs` |

**Available Endpoints**

| Endpoint | Type | Description |
|---|---|---|
| `GET /api/health` | Utility | Returns `{"status": "ok"}` for pre-flight checks. |
| `GET /api/cpu-bound?n=1000000` | Scenario | Loops `n` times doing float calculations (~100ms CPU work). Uses threads to avoid blocking Event Loop. |
| `GET /api/io-bound?delay=2.0` | Scenario | Non-blocking async sleep simulating external DB/network waits. |
| `POST /api/data` | Scenario | Accepts request body and returns 100 generated items (8-12 KB payload) to test network bandwidth and serialization speed. |

---

### ⚙️ engines/

Core script warehouse organized by engine types. Each subdirectory represents an executable context.

#### `engines/k6/`
* **Purpose**: Houses JavaScript-based test scenarios for [k6](https://k6.io).
* **Scenarios**: `smoke.js`, `stress_cpu.js`, `stress_io.js`, `stress_data.js`.
* **Execution**: `k6 run engines/k6/<scenario>.js`

#### `engines/jmeter/`
* **Purpose**: Houses Apache JMeter `.jmx` test plans.
* **Scenarios**: `ploadtesting_test_plan.jmx`.
* **Execution**: `jmeter -n -t ploadtesting_test_plan.jmx -l results.jtl`

#### `engines/loadrunner/` (Optional Future Integration)
* **Purpose**: Houses optional future enterprise integration points for commercial testing workflows.
* **Licensing**: LoadRunner is proprietary software owned by OpenText or its affiliates. `pLoadtesting` does not include, redistribute, sublicense, or modify LoadRunner binaries, proprietary libraries, or commercial assets. This future adapter requires a user-provided licensed installation of LoadRunner.

---

### 🖥️ control-plane/
* **Purpose**: Central command API for scheduling runs, tracking worker nodes status, and parsing result payloads.
* **Tech Stack**: Django, Django REST Framework, Celery, Redis.

---

### 🤖 workers/
* **Purpose**: Remote agent nodes listening for commands from the Control Plane to execute testing scripts locally and stream metrics.
* **Tech Stack**: Go / NodeJS.

---

## 🚦 Project Status & Roadmap

### 📌 Project Status
`pLoadtesting` is currently in an **early-stage preview / v0.1.0 preparation** phase. Core contracts and target verification are being stabilized.

### ✅ What Works Today
* **Target App**: Fully functioning target server with endpoints testing CPU bounds, async I/O waits, and data serialization.
* **Initial Engine Scripts**: Basic scripts and test plans for k6 and JMeter.
* **Docker Compose Skeleton**: Basic orchestration container setup for local validation of target-app.

### 🔮 Planned Features
* **Control Plane API MVP**: Basic Django REST APIs for registration, worker coordination, and scheduling.
* **Worker Agent MVP**: Lightweight agent daemon running scripts locally and notifying task completions.
* **Observability Integrations**: Collecting reports and outputting time-series metrics.

---

## 🛠️ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/minjay820/pLoadtesting.git
cd pLoadtesting

# 2. Spin up target-app
docker compose up target-app -d

# 3. Verify target endpoints
curl http://localhost:8000/api/health
curl "http://localhost:8000/api/cpu-bound?n=1000000"
curl "http://localhost:8000/api/io-bound?delay=1.0"
curl -X POST http://localhost:8000/api/data \
     -H "Content-Type: application/json" \
     -d '{"id": 1, "payload": "test"}'

# 4. View OpenAPI Docs
open http://localhost:8000/docs
```

---

## 🤝 Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for environment configuration requirements, branch naming guidelines, and Pull Request workflows.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 pLoadtesting contributors.

Please review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing sample scripts, container assets, or packaged releases.
