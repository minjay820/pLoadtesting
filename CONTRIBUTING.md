# Contributing to pLoadtesting

Thank you for your interest in contributing to pLoadtesting. This document outlines the current contribution workflow for the multi-engine load-testing ecosystem.

---

## 🛠️ Development Environment Requirements

To set up your development environment, you will need the following tools installed:

* **Docker & Docker Compose**: For orchestrating the reference target, diversified target app suite, Control Plane, Worker Agent, Redis, InfluxDB, and Grafana locally.
* **Python 3.11+**: Used by CI and compatible with the Python services. Local contributors may use a Python 3.12 virtual environment when needed.
* **k6**: Required for editing and validating JavaScript-based load-testing scripts locally.
* **JMeter**: Required for modifying or creating `.jmx` files.

---

## 📚 Documentation Trunk

`docs/v3/README.md` is the active documentation trunk for governed project work.

Before making a substantive change:

1. Read `docs/v3/README.md`.
2. Follow only the directly relevant child index or document.
3. Update the relevant `docs/v3/` document in the same change.
4. Add or update the current daily change log under `docs/v3/changes/daily/YYYY-MM-DD.md`.

Root documents such as `README.md`, `ROADMAP.md`, `SECURITY.md`, and `THIRD_PARTY_NOTICES.md` should stay concise and link to `docs/v3/` for detailed operating guidance.

## 🌿 Branch Naming Conventions

Please name your branches according to their purpose using the following prefixes:

* `feat/` for new features (e.g., `feat/worker-agent-mvp`)
* `fix/` for bug fixes (e.g., `fix/cpu-bound-overflow`)
* `docs/` for documentation updates (e.g., `docs/add-api-spec`)
* `chore/` for maintenance, packaging, or project-readiness work (e.g., `chore/project-readiness-v0.1.0`)
* `refactor/` for code refactoring with no functional change

---

## 💬 Commit Message Guidelines

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

## 🔄 PR Process

1. **Fork & Branch**: Create your feature branch from the latest `main` branch.
2. **Local Testing**: Run local tests (see testing guidelines below) to make sure your changes do not break existing logic.
3. **Commit**: Keep commits small and well-scoped.
4. **Open a PR**: Submit a pull request to our `main` branch. Make sure to fill in the PR template fully.
5. **CI & Review**: The PR will trigger automated checks in GitHub Actions. At least one maintainer must review and approve it.

---

## 🚀 Adding Scenarios

### k6 Scenarios
1. Go to [engines/k6/](engines/k6/).
2. Create or modify a `.js` scenario file.
3. Write your JS script using ES modules according to [k6 docs](https://k6.io/docs/).
4. Ensure it can run via command: `k6 run <script-name>.js`.
5. If the scenario is part of the target app catalog, add or update the matching `target-apps/task-templates/*.yaml` profile.

### JMeter Scenarios
1. Go to [engines/jmeter/](engines/jmeter/).
2. Create or edit a `.jmx` XML test plan using JMeter GUI.
3. Keep the target parameterized (e.g., `${__P(TARGET_HOST, localhost)}`).
4. Ensure it can run headlessly via command: `jmeter -n -t <plan>.jmx -l results.jtl`.
5. If it is an exact k6 counterpart, set reciprocal `equivalent_profile_id` metadata in the task templates.

### Target App Profiles

Target app scenarios are cataloged through:

* manifests in [target-apps/manifests/](target-apps/manifests/)
* task templates in [target-apps/task-templates/](target-apps/task-templates/)
* k6 samples in [engines/k6/](engines/k6/)
* JMeter samples in [engines/jmeter/](engines/jmeter/)

Profile-level k6/JMeter parity is tracked in [docs/v3/domains/p-loadtesting-target-profile-coverage.md](docs/v3/domains/p-loadtesting-target-profile-coverage.md). Keep this matrix and the automated template tests aligned when adding or changing profiles.

---

## 🐳 Local Verification

For the original reference target:

```bash
docker compose up target-app -d
curl http://localhost:8000/api/health
```

For the diversified local target app suite:

```bash
docker compose -f target-apps/docker-compose.target-apps.yml config --quiet
bash target-apps/scripts/smoke_docker_target_apps.sh
```

For Python and Control Plane checks:

```bash
python -m pytest target-app/ target-apps/tests -v
cd control-plane
python manage.py check
python manage.py test apps/ --verbosity=2
```

If your shell does not provide `python`, use the repo-managed virtual environments when available, for example `./.venv/bin/python` from the repository root and `./.venv/bin/python` inside `control-plane/`.

---

## 📋 Issue Triage Rules

* **Verification**: Verify if bug reports have a clear reproduction recipe and environment info.
* **Labeling**: Apply appropriate labels such as `bug`, `feature`, `documentation`, or `engine-integration`.
* **Prioritization**: Prioritize issues based on severity (e.g., blocking CI, service crashes) and align them with the upcoming milestones in [ROADMAP.md](ROADMAP.md).

---

## ⚖️ Third-party Licensing Rules

When contributing integrations for third-party tools (e.g. k6, JMeter, Prometheus, Grafana):
* Ensure any script or configuration template you commit complies with the original tool's license (e.g., Apache 2.0, AGPL, etc.).
* Do not bundle proprietary SDKs or binary distributions in your PR.
* Document any third-party license impacts or new notice entries required in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
