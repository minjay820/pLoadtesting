# External Database Runtime

This runbook defines control-plane PostgreSQL runtime settings for deployment smoke and release candidate validation. It uses placeholders only; do not paste live runtime values into this document or into command output.

## Runtime Database Selection

The Django settings module selects the database in this order:

1. `PLOADTESTING_DATABASE_URL`
2. `DATABASE_URL`
3. sqlite fallback at `control-plane/db.sqlite3`

The sqlite fallback is retained for local tests and no-env developer checks. Deployment smoke should provide one of the PostgreSQL URL variables through the deployment pack or host runtime.

## PostgreSQL Driver

The control-plane requirements include `psycopg[binary]`. The local smoke image installs it during `docker build`, so the same image can use PostgreSQL when runtime env is supplied.

Safe driver smoke:

```bash
docker run --rm local/ploadtesting-control-plane:0.1.0-rc.1 \
  python -c "import psycopg; print('psycopg ok')"
```

## Search Path

Preferred schema selection is through libpq runtime options:

```text
PGOPTIONS=-c search_path=plt,public
```

`PGOPTIONS` is consumed by the PostgreSQL client library and does not need to be parsed or printed by Django.

The settings module also accepts `PLOADTESTING_DB_SCHEMA` when `PGOPTIONS` is absent. This value must match:

```text
[a-zA-Z_][a-zA-Z0-9_]*
```

When valid, Django passes an equivalent PostgreSQL connection option for `search_path=<schema>,public`. Invalid values fail settings initialization without echoing the supplied value.

## Safe Validation

Use temporary env supplied by the operator or deployment pack. Confirm variable presence only; do not print values.

```bash
cd control-plane
PLOADTESTING_DATABASE_URL=<redacted> \
PGOPTIONS='-c search_path=plt,public' \
./.venv/bin/python manage.py check
```

Container migration plan validation:

```bash
docker run --rm \
  -e PLOADTESTING_DATABASE_URL \
  -e DATABASE_URL \
  -e PGOPTIONS='-c search_path=plt,public' \
  local/ploadtesting-control-plane:0.1.0-rc.1 \
  python manage.py migrate --plan
```

Do not run `python manage.py migrate` against an external database until the operator explicitly approves the migration step.

## Migration Boundary

The control-plane image startup command only starts the API server. It does not auto-migrate. Operators should run `showmigrations` and `migrate --plan` first, then run the actual migration as a separate, approved deployment action.

## Catalog Read API Access Policy

These read-only catalog endpoints are safe for compatible external clients without the shared API access header:

- `GET /api/tasks/templates/`
- `GET /api/tasks/templates/coverage/`

Task data and write routes remain protected:

- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/{id}/`
- `POST /api/tasks/{id}/results/`
- result, shard, and artifact metadata routes

The catalog endpoints expose static template and coverage metadata. They do not expose task records or result data.

Catalog output is registry/static metadata. It does not require task rows, result rows, or external database seed data. In deployment smoke images, the registry can use bundled safe demo profile definitions when the repo-root `target-apps` catalog is not present in the control-plane build context.

Safe demo profiles are for short, local-only deployment smoke. They must stay bounded, avoid third-party targets, and require no real credentials or runtime-only access material.

## Deployment Smoke Task Operation Flag

`PLOADTESTING_ENABLE_DEMO_TASK_API` defaults to disabled. Set it only for bounded deployment smoke when a compatible external client needs to submit and inspect a safe demo task without broader task operation access.

When enabled, Core accepts only:

- `target_app_id=echo-api`, `target_profile_id=echo-k6-smoke`
- `target_app_id=echo-api`, `target_profile_id=echo-jmeter-smoke`

The flag does not open arbitrary task creation, long-running profiles, third-party targets, worker result callbacks, or artifact download. It also does not replace the formal API authentication strategy planned for non-smoke operation.

Controlled demo task execution still requires a registered compatible worker with the matching engine capability and the existing internal/shared callback configuration. Core attempts one immediate dispatch after safe demo task creation. When no compatible idle worker is present, the task remains `pending` and records a diagnostic `error_message`; bounded polling should report that worker capacity is missing instead of treating the task as completed.

For non-sharded controlled demo tasks, `GET /api/tasks/{id}/shard-plan/` returns a single-task metadata response with `mode=single`, `shards=[]`, and `status=not_applicable`. That response is the expected read model for safe demo profiles that do not use manual shard distribution.

Safe container check:

```bash
docker run --rm \
  -e PLOADTESTING_ENABLE_DEMO_TASK_API=true \
  local/ploadtesting-control-plane:0.1.0-rc.1 \
  python manage.py check
```

## Logging Boundary

Settings code must not print database URLs, runtime-only values, or sensitive values. Validation reports should describe which variable names were used and whether the engine points to PostgreSQL, without printing the full URL.
