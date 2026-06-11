# Legacy Migration Staging

This area is for mirrored pre-v3 documentation. During migration, do not delete or rewrite original legacy documents.

## Migration Rule

1. Copy legacy content into `docs/v3/legacy/` first.
2. Record the source, mirrored path, normalized target path, migration status, and rationale in [leaf-normalization-map.md](leaf-normalization-map.md).
3. Normalize the content into the appropriate active area:
   - `docs/v3/domains/`
   - `docs/v3/specs/`
   - `docs/v3/adr/`
   - `docs/v3/runbooks/`
4. Update the relevant README index and daily change log in the same session.

## Current Status

No legacy documents were mirrored in the governance initialization session.

## Pending Legacy Candidates

| Legacy source | Likely target area | Notes |
|---|---|---|
| `README.md` | domains, runbooks | Project overview, architecture, quick start, documentation index. |
| `ROADMAP.md` | domains, specs | Roadmap and milestone context. |
| `CONTRIBUTING.md` | runbooks | Contributor workflow and validation expectations. |
| `SECURITY.md` | runbooks | Security policy and reporting process. |
| `THIRD_PARTY_NOTICES.md` | domains, runbooks | Third-party component notices. |
| `control-plane/ARCHITECTURE.md` | domains, specs, adr | Control Plane model, API, scheduling, and architecture rationale. |
| `docs/architecture-interaction.md` | domains, specs | System interactions and state diagrams. |
| `docs/k6-smoke-test-guide.md` | specs, runbooks | k6 execution and smoke validation. |
| `docs/local-validation-guide.md` | runbooks | Docker Compose validation and troubleshooting. |
| `docs/observability-guide.md` | specs, runbooks | InfluxDB and Grafana setup/validation. |
| `docs/oss-readiness-checklist.md` | runbooks | OSS release readiness checks. |
| `engines/k6/README.md` | specs, runbooks | k6 engine usage and script contracts. |
| `engines/jmeter/README.md` | specs, runbooks | JMeter engine usage and report workflow. |

Generated or vendored documentation under report templates or third-party dependency folders should be reviewed before migration and may be excluded if it is not project-authored documentation.
