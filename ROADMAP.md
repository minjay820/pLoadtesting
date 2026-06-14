# pLoadtesting Roadmap

This roadmap summarizes the current release direction for the `pLoadtesting` ecosystem. Detailed planning lives in the active docs trunk under [docs/v3/README.md](docs/v3/README.md).

---

## Current Baseline

pLoadtesting is a local-preview multi-engine load-testing ecosystem with:

* a Django/DRF Control Plane for workers, tasks, template-driven task creation, and results
* a FastAPI Worker Agent for k6 and JMeter execution
* a diversified local `target-apps` suite with manifests, task templates, Docker smoke validation, and profile-level k6/JMeter coverage
* InfluxDB and Grafana observability support in the local compose stack

The current completion assessment is maintained in [docs/v3/domains/p-loadtesting-phase-completion.md](docs/v3/domains/p-loadtesting-phase-completion.md).

---

## Release Horizon Model

### Horizon 1: Local Preview Foundation

**Goal**: Keep the local end-to-end flow reproducible and safe.

**Status**: Implemented for current preview scope.

**Key Components**

* Reference `target-app/`
* Diversified `target-apps/` catalog
* k6 and JMeter sample coverage
* Control Plane task/worker/result APIs
* Worker Agent registration, heartbeat, dispatch, execution, and result callback
* CI and local smoke validation

### Horizon 2: Catalog And Validation Depth

**Goal**: Make target profile coverage auditable and keep engine parity manageable.

**Status**: Implemented for the current strict profile rule.

**Key Components**

* Manifest-driven task templates
* Reciprocal k6/JMeter `equivalent_profile_id` metadata
* Authoritative target profile coverage matrix
* Docker runtime smoke validation
* Local-only bounded target workloads for HTTP, SSE, WebSocket, DB-heavy, file-heavy, and demo-only auth-heavy branches

The active coverage matrix is [docs/v3/domains/p-loadtesting-target-profile-coverage.md](docs/v3/domains/p-loadtesting-target-profile-coverage.md).

### Horizon 3: Operator Experience And Stable APIs

**Goal**: Prepare dashboard, external API, access, and distributed deployment work without overloading the current preview runtime.

**Status**: Planned.

**Key Components**

* Web dashboard MVP over tasks, workers, results, and task templates
* Stable external `/api/v1` contract
* Scoped API access model to replace the single shared preview token over time
* Three-host/cross-subnet deployment hardening
* Dashboard/API contract tests

Planning references:

* [docs/v3/domains/p-loadtesting-web-dashboard.md](docs/v3/domains/p-loadtesting-web-dashboard.md)
* [docs/v3/specs/external-api-v1.md](docs/v3/specs/external-api-v1.md)
* [docs/v3/specs/api-token-auth.md](docs/v3/specs/api-token-auth.md)
* [docs/v3/runbooks/distributed-deployment.md](docs/v3/runbooks/distributed-deployment.md)
* [docs/v3/roadmap/github-issues-dashboard-api-deployment.md](docs/v3/roadmap/github-issues-dashboard-api-deployment.md)

### Horizon 4: Optional Advanced Integrations

**Goal**: Add larger integrations only after the preview runtime, API contract, and access model are stable.

**Status**: Deferred.

**Potential Work**

* Enterprise engine adapters through user-provided licensed installations
* Heavier observability and artifact retention policies
* Deployment-specific worker capacity controls
* Additional target app families only when they remain deterministic, bounded, and local/controlled-environment safe

---

## Non-Goals And Out Of Scope

* **Unauthorized testing**: Users must only test systems they own or have explicit permission to test.
* **Redistributing third-party engines**: pLoadtesting does not package or sublicense k6, Apache JMeter, or OpenText LoadRunner. Users are responsible for licensing and installation where required.
* **Public multi-tenant hosting**: The Control Plane is designed for internal team deployment, not public multi-tenant SaaS hosting.
* **Direct cloud autoscaling**: pLoadtesting does not manage cloud provider VM or node scaling out of the box.
* **Production-grade access controls today**: Scoped access is planned; the current shared preview token is not a full production authorization system.
