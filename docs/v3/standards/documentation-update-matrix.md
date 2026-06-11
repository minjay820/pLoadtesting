# Documentation Update Matrix

Use this matrix to decide which `docs/v3/` surfaces must be updated for a change.

| Change type | Required docs update | Daily log required | Commit normally required |
|---|---|---:|---:|
| Code logic change | Relevant domain, spec, ADR, or runbook | Yes | Yes |
| Data model change | Spec and possibly domain or ADR | Yes | Yes |
| API behavior change | API spec, runbook if operational impact exists | Yes | Yes |
| UI behavior change | Spec or runbook describing user workflow | Yes | Yes |
| Runtime script change | Runbook and configuration notes | Yes | Yes |
| Startup or deployment setting change | Runbook and configuration notes | Yes | Yes |
| Environment variable change | Runbook or spec defining configuration | Yes | Yes |
| Docker or Compose change | Runbook and deployment/operations docs | Yes | Yes |
| CI/CD change | Runbook or validation workflow docs | Yes | Yes |
| Documentation governance change | `AGENTS.md`, `docs/v3/README.md`, all standards, daily log | Yes | Yes |
| New ADR | `docs/v3/adr/README.md` and the ADR | Yes | Usually |
| Legacy mirroring | `docs/v3/legacy/`, leaf normalization map, target-area README if normalized | Yes | Usually |
| Test strategy or validation flow change | Runbook or spec | Yes | Usually |
| Typo-only edit | Usually only touched file | No, unless meaningful | No, unless requested |
| Analysis-only session | None | No | No |

## Repository Examples

- Changes to `control-plane/` models, serializers, Celery tasks, or API routes usually require specs or runbooks for orchestration behavior.
- Changes to `workers/agent.py` usually require worker execution and engine runbook updates.
- Changes to `engines/k6/` or `engines/jmeter/` usually require engine specs or runbooks.
- Changes to `docker-compose.yml`, Dockerfiles, InfluxDB, Grafana, or Redis/Celery settings usually require deployment or local validation runbook updates.
- Changes to `.github/workflows/ci.yml` usually require validation workflow documentation updates.
