# 🌌 pLoadtesting

> **Multi-engine automated load testing ecosystem for k6, JMeter, worker agents, control plane orchestration, and reproducible performance reports.**

[![CI](https://github.com/minjay820/pLoadtesting/actions/workflows/ci.yml/badge.svg)](https://github.com/minjay820/pLoadtesting/actions/workflows/ci.yml)
[![Phase](https://img.shields.io/badge/Phase-MVP%20Preview-blueviolet)](ROADMAP.md)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)](ROADMAP.md)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

> [!WARNING]
> **Safety & Production Readiness Warnings:**
> * This project is an early-stage preview (v0.1.0).
> * Use this project **only** for authorized performance testing against systems you own or have explicit permission to test.
> * Do not test systems you do not own or do not have explicit permission to test.
> * **Do not expose** Control Plane or Worker endpoints to the public internet without authentication, authorization, network isolation, and rate limiting.
> * The Control Plane and Worker Agent components are **not production-ready yet**.

---

## 📐 Architecture Blueprint

```
  ┌──────────────────────────────────────────────────────┐
  │                   Control Plane :9000                │
  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
  │  │  Django ORM │  │ Celery Beat  │  │  REST API  │  │
  │  │  (SQLite)   │  │  (Redis)     │  │  (DRF)     │  │
  │  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘  │
  └─────────┼────────────────┼────────────────┼──────────┘
            │                │ dispatch        │ REST
            │        ┌───────▼──────────┐      │
            │        │  Worker Agent    │      │
            │        │  FastAPI :8100   │      │
            │        │  k6 | JMeter     │      │
            │        └───────┬──────────┘      │
            │                │ heartbeat/result │
            └────────────────┴─────────────────┘
                             │ HTTP Load
                    ┌────────▼────────────┐
                    │    Target App :8000  │
                    │  FastAPI (CPU/IO/Data│
                    └─────────────────────┘
```

| Component | Tech Stack | Port |
|---|---|---|
| **Target App** | Python 3.11 + FastAPI + Uvicorn | `8000` |
| **Control Plane** | Django 5 + DRF + Celery + Redis | `9000` |
| **Worker Agent** | FastAPI + k6 + JMeter 5.6.3 | `8100` (internal) |
| **Message Broker** | Redis 7 | `6379` (internal) |
| **Metrics Store** | InfluxDB v2.7 | `8086` |
| **Dashboard** | Grafana OSS 11.6 | `3000` |

---

## 🗂️ Directory Structure

```
pLoadtesting/
│
├── target-app/               # Reference API server used as a load testing target
├── engines/                  # Load testing scripts and scenario assets
│   ├── k6/                   # k6 test scripts (smoke, stress_cpu, stress_io, stress_data)
│   ├── jmeter/               # JMeter test plans (.jmx)
│   └── loadrunner/           # Optional future enterprise engine adapter
│
├── control-plane/            # Orchestration API (Django + Celery + Redis)
│   └── ARCHITECTURE.md       # Detailed Control Plane design document
├── workers/                  # Remote execution agent (FastAPI)
├── docs/                     # Documentation
│   ├── architecture-interaction.md   # Mermaid interaction diagrams
│   ├── k6-smoke-test-guide.md        # k6 usage guide & expected output
│   ├── local-validation-guide.md     # Docker Compose debugging guide
│   └── oss-readiness-checklist.md   # OSS release checklist
├── docker-compose.yml        # Full ecosystem orchestration
└── README.md                 # This file
```

---

## 📦 Components

### 🎯 target-app/

A standardized, deployable reference target API service.

| Item | Details |
|---|---|
| Tech Stack | **Python 3.11 + FastAPI + Uvicorn (uvloop)** |
| Deployment | Dockerized — `docker compose up target-app -d` (Port 8000) |
| Interactive Spec | Swagger UI at `http://localhost:8000/docs` |

**Available Endpoints**

| Endpoint | Type | Description |
|---|---|---|
| `GET /api/health` | Utility | Returns `{"status": "ok"}` for pre-flight checks |
| `GET /api/cpu-bound?n=1000000` | Scenario | Float-multiply loop simulating CPU-bound work (~100ms) |
| `GET /api/io-bound?delay=2.0` | Scenario | Non-blocking async sleep simulating I/O wait |
| `POST /api/data` | Scenario | Accepts body, returns 100 generated items (~8-12 KB payload) |

---

### ⚙️ engines/

Core script warehouse organized by engine type.

#### `engines/k6/`
* **Scenarios**: `smoke.js`, `stress_cpu.js`, `stress_io.js`, `stress_data.js`
* **Usage**: See [k6 Smoke Test Guide](docs/k6-smoke-test-guide.md)

#### `engines/jmeter/`
* **Scenarios**: `ploadtesting_test_plan.jmx`
* **Execution**: `jmeter -n -t ploadtesting_test_plan.jmx -l results.jtl`

#### `engines/loadrunner/` (Optional Future Integration)
> **Licensing Note**: pLoadtesting does not include, redistribute, sublicense, or modify LoadRunner binaries. This adapter requires a user-provided licensed installation.

---

### 🖥️ control-plane/

Central orchestration API managing workers, tasks, and results.

* **Tech Stack**: Django 5, Django REST Framework, Celery, Redis
* **Core Models**: `WorkerNode` (7 states), `LoadTestTask` (7 states), `TestResult`
* **Celery Beat Tasks**: `mark_stale_workers` (30s), `dispatch_pending_tasks` (periodic)
* **Architecture Details**: See [Control Plane ARCHITECTURE.md](control-plane/ARCHITECTURE.md)
* **Interaction Diagrams**: See [architecture-interaction.md](docs/architecture-interaction.md)

---

### 🤖 workers/

Remote agent nodes that execute load test scripts and report results.

* **Tech Stack**: FastAPI + `psutil` + k6 + Apache JMeter 5.6.3
* **Heartbeat**: Every 10 seconds — sends CPU/Memory metrics to Control Plane
* **Engines**: k6 (JSON output parsing) + JMeter (`.jtl` CSV parsing)
* **Metrics Reported**: RPS, p90/p95/p99 response times, error rate, peak VUs

---

## 🚦 Project Status

| Feature | Status |
|---|---|
| Target App (CPU/IO/Data endpoints) | ✅ Complete |
| k6 Engine Integration | ✅ Complete |
| JMeter Engine Integration | ✅ Complete |
| Control Plane REST API | ✅ Complete |
| Worker ↔ Control Plane Heartbeat | ✅ Complete |
| Celery Task Dispatch | ✅ Complete |
| API Token Authentication | ✅ Complete |
| Docker Compose Full Stack | ✅ Complete |
| Grafana + InfluxDB Observability | ✅ Complete (Phase 6) |
| Web UI Dashboard | 🔜 Planned (Phase 7) |

---

## 🛠️ Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/minjay820/pLoadtesting.git
cd pLoadtesting

# 2. (Optional) Configure API token
echo "PLOADTESTING_API_TOKEN=dev-api-token-change-me" > .env

# 3. Build and start all services
docker compose up --build -d

# 4. Verify all services are healthy
docker compose ps

# 5. Verify Target App
curl http://localhost:8000/api/health
# → {"status":"ok"}

# 6. Verify Control Plane (Worker Agent should have registered via heartbeat after ~10s)
curl http://localhost:9000/api/workers/ \
  -H "X-PLoadtesting-Api-Token: dev-api-token-change-me"

# 7. Run k6 smoke test locally (requires k6 installed)
k6 run engines/k6/smoke.js
```

For full local validation steps, troubleshooting, and end-to-end test flows, see the **[Docker Compose Local Validation Guide](docs/local-validation-guide.md)**.

---

## 📚 Documentation

| Document | Description |
|---|---|
| [docs/architecture-interaction.md](docs/architecture-interaction.md) | Mermaid interaction & state machine diagrams |
| [docs/k6-smoke-test-guide.md](docs/k6-smoke-test-guide.md) | k6 smoke test usage guide & expected output |
| [docs/local-validation-guide.md](docs/local-validation-guide.md) | Docker Compose debugging & validation guide |
| [docs/observability-guide.md](docs/observability-guide.md) | InfluxDB v2 + Grafana 快速啟動與 Dashboard 說明 |
| [docs/oss-readiness-checklist.md](docs/oss-readiness-checklist.md) | OSS release checklist |
| [control-plane/ARCHITECTURE.md](control-plane/ARCHITECTURE.md) | Control Plane detailed design |
| [ROADMAP.md](ROADMAP.md) | Project roadmap & milestones |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [SECURITY.md](SECURITY.md) | Security policy |

---

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for environment configuration requirements, branch naming guidelines, and Pull Request workflows.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 pLoadtesting contributors.

Please review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before redistributing sample scripts, container assets, or packaged releases.
