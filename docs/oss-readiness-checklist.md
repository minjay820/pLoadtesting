# OSS Readiness Checklist

This checklist is used to evaluate the readiness of the `pLoadtesting` repository before applying to OSS support programs or declaring a stable v0.1.0 release.

## 📋 Repository Checklist

- [x] **License**: Project uses a standard open-source license (`LICENSE` containing the MIT License text).
- [x] **README**: Updated with clear naming, tagline, current full architecture (Control Plane + Worker Agent + dual engine), feature status table, documentation links, and quick start.
- [x] **CONTRIBUTING**: Defined local environment setup, branching, commit, scenario integration, and licensing rules.
- [x] **ROADMAP**: Clearly separated version scopes, goals, and non-goals from v0.1.0 to v1.0.0.
- [x] **SECURITY**: Established a policy on reporting vulnerabilities, handling credentials, and load-test authorizations.
- [x] **Third-party Notices**: Provided details of third-party engine licensing restrictions in `THIRD_PARTY_NOTICES.md`.
- [x] **GitHub Templates**:
  - [x] Issue template for Bug Report
  - [x] Issue template for Feature Request
  - [x] Issue template for Engine Integration
  - [x] Issue template for Documentation
  - [x] Pull Request template
- [x] **GitHub Actions CI**: Three-job pipeline covering Target App tests, Control Plane Django tests, and Worker Agent lint.
- [x] **Test Coverage**: Target App endpoints covered by automated tests; Control Plane dispatch and result handling covered by Django unit tests.

---

## 📁 Documentation Checklist

- [x] **Architecture Interaction Diagrams** (`docs/architecture-interaction.md`):
  - [x] Heartbeat sequence diagram (Worker → Control Plane, Celery Beat stale check)
  - [x] Task dispatch sequence diagram (9-step full lifecycle)
  - [x] Task execution & result collection diagram (k6 / JMeter parsing)
  - [x] LoadTestTask state machine diagram
  - [x] System topology overview (Docker network)
- [x] **k6 Smoke Test Guide** (`docs/k6-smoke-test-guide.md`):
  - [x] Prerequisites and installation instructions
  - [x] Local execution commands (direct & via Worker Agent)
  - [x] Full expected output with annotated metrics
  - [x] Key metrics interpretation table
  - [x] Common error troubleshooting (5 scenarios)
- [x] **Local Validation Guide** (`docs/local-validation-guide.md`):
  - [x] Service overview table
  - [x] Step-by-step startup guide
  - [x] Endpoint health verification commands
  - [x] End-to-end test flow script
  - [x] Common service management commands
  - [x] FAQ troubleshooting (5 common issues)
  - [x] Resource monitoring guidance

---

## 🚀 Release Checklist (v0.1.0 Readiness)

- [ ] Clean up temporary files, logs (`*.log`), caches (`__pycache__`), and local virtual environments.
- [ ] Ensure all local test cases pass under standard Python 3.11 environment.
- [ ] Tag the repository commit with release version: `git tag -a v0.1.0 -m "Release v0.1.0"`.
- [ ] Update GitHub About metadata:
  - **Description**: Multi-engine automated load testing ecosystem for k6, JMeter, worker agents, control plane orchestration, and reproducible performance reports.
  - **Topics**: `load-testing`, `performance-testing`, `k6`, `jmeter`, `fastapi`, `distributed-systems`, `devops`, `sre`.
- [ ] Create GitHub Release with release notes summarizing v0.1.0 changes.
