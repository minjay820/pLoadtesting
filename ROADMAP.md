# pLoadtesting Roadmap

This roadmap outlines the milestones and release goals for the pLoadtesting ecosystem.

---

## 🗺️ Milestone Releases

### 📌 v0.1.0: OSS Readiness
* **Goals**: Establish project governance, Open Source hygiene, baseline documentation, automated CI testing, and contribution templates.
* **Scope**:
  * Formalize licensing and attribution (`LICENSE`, `THIRD_PARTY_NOTICES.md`).
  * Set up GitHub templates (Issue templates, Pull Request templates, and security guidelines).
  * Build basic unit tests for `target-app` and configure lightweight GitHub Actions workflow for Python verification.
  * Update documentation files (`README.md`, `CONTRIBUTING.md`, `ROADMAP.md`, `SECURITY.md`).
* **Non-Goals**:
  * Developing new UI frameworks or backend orchestrations.
  * Adding complex, multi-service end-to-end integration tests.

### 📌 v0.2.0: Control Plane MVP
* **Goals**: Launch a minimum viable Control Plane to model work tasks and manage workers.
* **Scope**:
  * Develop the Django + Django Rest Framework (DRF) backend structure in `control-plane`.
  * Create schemas and database migrations for `WorkerNode`, `LoadTestTask`, and `TestResult`.
  * Set up Celery & Redis task broker configurations for async job scheduling.
* **Non-Goals**:
  * Complete worker agent integration.
  * Fully featured frontend UI (Mock APIs or simple HTML endpoints only).

### 📌 v0.3.0: Worker Agent MVP
* **Goals**: Enable worker agents to receive tasks from the Control Plane and execute local runs.
* **Scope**:
  * Implement worker agent daemon using Go or NodeJS to fetch tasks from the Django Control Plane.
  * Implement execution wrapper for running `k6` and `JMeter` scenarios in subprocesses.
  * Forward execution status and exit codes back to the Control Plane database.
* **Non-Goals**:
  * Real-time streaming log aggregation.
  * Distributed execution logic across multiple physical target nodes.

### 📌 v0.4.0: Dashboard MVP
* **Goals**: Build the Control Plane user interface for simple configuration and execution status monitoring.
* **Scope**:
  * Create Next.js / React interactive portal in `control-plane/web`.
  * Display lists of online Workers and active/completed LoadTestTasks.
  * Add forms to construct and launch test tasks with specific configurations.
* **Non-Goals**:
  * Granular time-series metrics rendering.
  * Advanced user authorization (RBAC).

### 📌 v0.5.0: Report Artifact and Observability
* **Goals**: Integrate structured reports collection and basic real-time metrics visualizations.
* **Scope**:
  * Aggregate resulting test outputs (e.g. k6 JSON summary, JMeter `.jtl` or HTML reports).
  * Configure containerized Prometheus/InfluxDB and pre-built Grafana dashboards.
  * Expose standard export APIs for test summaries.
* **Non-Goals**:
  * Enterprise data retention policies.

### 📌 v1.0.0: Production-Ready Distributed Platform
* **Goals**: Provide a reliable, scalable, and production-ready distributed load testing platform.
* **Scope**:
  * Support distributed multi-worker agent scheduling with request rate balancing.
  * Full E2E verification tests.
  * High-availability setup options for Control Plane.
  * Advanced SLA threshold assertions and alerting integrations.
* **Non-Goals**:
  * Dynamic cluster provisioning (Kubernetes auto-scaler).
