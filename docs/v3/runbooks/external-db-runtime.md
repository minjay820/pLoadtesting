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

## Logging Boundary

Settings code must not print database URLs, runtime-only values, or sensitive values. Validation reports should describe which variable names were used and whether the engine points to PostgreSQL, without printing the full URL.
