# OSS Readiness Checklist

This checklist is used to evaluate the readiness of the `pLoadtesting` repository before applying to OSS support programs or declaring a stable v0.1.0 release.

## 📋 Repository Checklist

- [x] **License**: Project uses a standard open-source license (`LICENSE` containing the MIT License text).
- [x] **README**: Updated with clear naming, tagline, current features, roadmap status, and links to licenses.
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
- [x] **GitHub Actions CI**: Automated lint/import checks and unit test executions on push/PR.
- [x] **Test Coverage**: Basic endpoints `/api/health`, `/api/cpu-bound`, `/api/io-bound`, and `/api/data` covered by automated tests.

---

## 🚀 Release Checklist (v0.1.0 Readiness)

- [ ] Clean up temporary files, logs (`*.log`), caches (`__pycache__`), and local virtual environments.
- [ ] Ensure all local test cases pass under standard Python 3.11 environment.
- [ ] Tag the repository commit with release version: `git tag -a v0.1.0 -m "Release v0.1.0"`.
- [ ] Update GitHub About metadata:
  - **Description**: Multi-engine automated load testing ecosystem for k6, JMeter, worker agents, control plane orchestration, and reproducible performance reports.
  - **Topics**: `load-testing`, `performance-testing`, `k6`, `jmeter`, `fastapi`, `distributed-systems`, `devops`, `sre`.
