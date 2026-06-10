# pLoadtesting Roadmap

This roadmap outlines the milestones and release goals for the `pLoadtesting` ecosystem.

---

## 🗺️ Release Horizon Model

To maintain focus and avoid over-committing on complex features prematurely, we categorize development milestones into three Horizons:

### 🌅 Horizon 1: Core Ecosystem & k6 Integration (Current Focus)
* **Goal**: Establish a functional local end-to-end flow using open-source engines and stable core contracts.
* **Key Components**:
  * **v0.1.0 (OSS Readiness Preview)**: Base repo hygiene, license compliance, GitHub templates, and basic CI verification.
  * **v0.2.0 (Control Plane API Contract)**: Core REST APIs in the Django-based Control Plane to define `WorkerNode`, `LoadTestTask`, and `TestResult` data contracts.
  * **v0.3.0 (Worker Agent MVP)**: Lightweight agent daemon that receives jobs, runs local k6 scripts, and reports exit codes.
  * **Basic Report Artifacts**: Simple JSON-based test outcome collation.

### 🌤️ Horizon 2: JMeter Support & Expanded Reporting
* **Goal**: Add robust support for Apache JMeter test scenarios and intermediate-level reports.
* **Key Components**:
  * **JMeter Executor**: Worker agent updates to launch headless JMeter scenarios using user-provided XML configurations.
  * **Report Parsing**: Automated parsing of `.jtl` output logs and formatting into readable summaries.
  * **Web Dashboard MVP**: Simple user interface for task dispatching and live worker status monitoring.

### 🌌 Horizon 3: Advanced Integrations & Observability (Long-Term)
* **Goal**: Support production-scale operations, distributed synchronization, and optional enterprise integrations.
* **Key Components**:
  * **Distributed Worker Coordination**: Basic worker rate control and cluster scaling.
  * **Time-Series Observability**: Grafana + Prometheus/InfluxDB templates for real-time visualization.
  * **Optional Enterprise Engine Adapters**: Compatible configuration integration points for enterprise tools (e.g. LoadRunner scripts), subject to user-provided licensed software installations. *pLoadtesting will not package or redistribute proprietary tools or licenses.*

---

## 🚫 Non-Goals & Out of Scope
* **Redistributing Third-Party Engines**: We do not package or sublicense k6, Apache JMeter, or OpenText LoadRunner. Users are responsible for installing these on workers.
* **SaaS Multi-Tenancy**: The Control Plane is designed for internal team deployment, not public multi-tenant SaaS hosting.
* **Direct Auto-Scaling of Cloud Infrastructure**: We do not manage cloud provider VM/Node scaling out of the box.
