# Contributing to pLoadtesting

Thank you for your interest in contributing to pLoadtesting! This document outlines the guidelines, workflows, and standards for contributing to the repository.

---

## 🛠️ 開發環境需求 (Development Environment Requirements)

To set up your development environment, you will need the following tools installed:

* **Docker & Docker Compose**: For orchestrating the target application and load testing engines locally.
* **Python 3.11+**: Used for running the `target-app` and test suite. We recommend using a virtual environment (`venv`).
* **k6**: Required for editing and validating JavaScript-based load-testing scripts locally.
* **JMeter**: Required for modifying or creating `.jmx` files.

---

## 🌿 Branch 命名規則 (Branch Naming Conventions)

Please name your branches according to their purpose using the following prefixes:

* `feat/` for new features (e.g., `feat/worker-agent-mvp`)
* `fix/` for bug fixes (e.g., `fix/cpu-bound-overflow`)
* `docs/` for documentation updates (e.g., `docs/add-api-spec`)
* `chore/` for maintenance, packaging, or OSS hygiene (e.g., `chore/oss-readiness-v0.1.0`)
* `refactor/` for code refactoring with no functional change

---

## 💬 Commit Message 建議 (Commit Message Guidelines)

We encourage structured git commit messages following the Conventional Commits specification:

```text
<type>(<scope>): <subject>

[optional body]
```

**Types:**
* `feat`: A new feature
* `fix`: A bug fix
* `docs`: Documentation only changes
* `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc.)
* `refactor`: A code change that neither fixes a bug nor adds a feature
* `test`: Adding missing tests or correcting existing tests
* `chore`: Changes to the build process or auxiliary tools and libraries

**Example:**
`feat(target-app): add endpoints for CPU-bound simulations`

---

## 🔄 Pull Request 流程 (PR Process)

1. **Fork & Branch**: Create your feature branch from the latest `main` branch.
2. **Local Testing**: Run local tests (see testing guidelines below) to make sure your changes do not break existing logic.
3. **Commit**: Keep commits small and well-scoped.
4. **Open a PR**: Submit a pull request to our `main` branch. Make sure to fill in the PR template fully.
5. **CI & Review**: The PR will trigger automated checks in GitHub Actions. At least one maintainer must review and approve it.

---

## 🚀 如何新增 k6 / JMeter Scenario (Adding Scenarios)

### k6 Scenarios
1. Go to [engines/k6/](file:///Users/minjay/myAntigravity/pLoadtesting/engines/k6).
2. Create or modify a `.js` scenario file.
3. Write your JS script using ES modules according to [k6 docs](https://k6.io/docs/).
4. Ensure it can run via command: `k6 run <script-name>.js`.

### JMeter Scenarios
1. Go to [engines/jmeter/](file:///Users/minjay/myAntigravity/pLoadtesting/engines/jmeter).
2. Create or edit a `.jmx` XML test plan using JMeter GUI.
3. Keep the target parameterized (e.g., `${__P(TARGET_HOST, localhost)}`).
4. Ensure it can run headlessly via command: `jmeter -n -t <plan>.jmx -l results.jtl`.

---

## 🐳 如何確認 Docker Compose / target-app 可啟動 (Local Verification)

Ensure you can launch the target application locally via Docker:

```bash
# Start target-app
docker compose up target-app -d

# Verify app is healthy
curl http://localhost:8000/api/health
```

To run the target-app without Docker (for Python dev/debugging):

```bash
cd target-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 📋 Issue Triage 原則 (Issue Triage Rules)

* **Verification**: Verify if bug reports have a clear reproduction recipe and environment info.
* **Labeling**: Apply appropriate labels such as `bug`, `feature`, `documentation`, or `engine-integration`.
* **Prioritization**: Prioritize issues based on severity (e.g., blocking CI, service crashes) and align them with the upcoming milestones in [ROADMAP.md](file:///Users/minjay/myAntigravity/pLoadtesting/ROADMAP.md).

---

## ⚖️ 第三方工具授權注意事項 (Third-party Licensing Rules)

When contributing integrations for third-party tools (e.g. k6, JMeter, Prometheus, Grafana):
* Ensure any script or configuration template you commit complies with the original tool's license (e.g., Apache 2.0, AGPL, etc.).
* Do not bundle proprietary SDKs or binary distributions in your PR.
* Document any third-party license impacts or new notice entries required in [THIRD_PARTY_NOTICES.md](file:///Users/minjay/myAntigravity/pLoadtesting/THIRD_PARTY_NOTICES.md).
