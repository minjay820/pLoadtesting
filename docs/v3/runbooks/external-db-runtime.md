# External Database Runtime

This runbook defines control-plane database runtime settings for deployment smoke and release candidate validation. It uses placeholders only; do not paste live runtime values into this document or into command output.

## Database Support Baseline

pLoadtesting must support at least these database modes:

- sqlite: local development, demos, single-node basic installs, and fast no-env validation.
- PostgreSQL: production, multi-user operation, long-lived task/result history, and deployments that run workers or schedulers beyond a local demo.

The same Django migrations must remain compatible with both modes. sqlite validation may run directly in local tests. PostgreSQL validation should first use settings checks and migration planning with redacted runtime values; do not run production migrations until a separate migration gate is approved.

## Runtime Database Selection

The Django settings module selects the database in this order:

1. `PLOADTESTING_DATABASE_URL`
2. `DATABASE_URL`
3. sqlite fallback at `control-plane/db.sqlite3`

The sqlite fallback is retained for local tests, demos, basic single-node installation, and no-env developer checks. Deployment smoke and production should provide one of the PostgreSQL URL variables through the deployment pack or host runtime.

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

## Initial Admin Bootstrap

pLoadtesting must not ship a default admin username or password. A fresh installation should create the first management account through an explicit one-shot command after migrations have been applied:

```bash
python manage.py create_initial_admin \
  --username <admin-username> \
  --email <optional-email> \
  --password-file /path/to/private/admin-password.txt
```

The password file must be private. On POSIX systems the command rejects files that are readable, writable, or executable by group/other users. A typical operator-controlled file mode is:

```bash
chmod 600 /path/to/private/admin-password.txt
```

Command behavior:

- Creates a staff/superuser account only when no superuser exists.
- Refuses to create or overwrite accounts once a superuser exists.
- Refuses to promote an existing normal user with the requested username.
- Validates the password with Django password validators.
- Does not print the password.

Interactive password entry is available when `--password-file` is omitted, but production deployment gates should prefer an ignored private password file so the secret is not stored in shell history or tracked documentation.

Production use of `create_initial_admin` is a DB-write action. It must be run only in a separate owner-approved admin-user gate, after route/runtime smoke has verified the management surface and before the first operator login. Password reset is a separate lifecycle operation and must not be bundled with the first-admin bootstrap gate.

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

For deployment smoke, the worker must register into the same Control Plane runtime and therefore the same external database-backed worker registry. Configure only variable names in deployment material, not live values:

- `CONTROL_PLANE_URL`
- `WORKER_NAME`
- `WORKER_PORT`
- `WORKER_CAPABILITIES`
- `WORKER_ADVERTISE_IP` when Core cannot reach the automatically detected worker IP
- `PLOADTESTING_API_TOKEN`

`DJANGO_ALLOWED_HOSTS` must include the host name in `CONTROL_PLANE_URL`; otherwise Worker registration can be rejected before it reaches the worker registry. This is a deployment setting, not a reason to make task APIs public.

## Admin Host Security Settings

The control-plane settings module accepts admin-host hardening settings through environment variables so downstream deployments can expose Django admin behind a separate protected hostname without changing source code. These settings are inactive by default and preserve the previous local/runtime behavior when unset.

Supported variable names and formats:

- `DJANGO_ALLOWED_HOSTS`: comma-separated host list. Add an admin hostname only after a separate admin route/security gate approves it.
- `DJANGO_CSRF_TRUSTED_ORIGINS`: comma-separated origins, for example `https://plt.myii.cc`.
- `DJANGO_SECURE_PROXY_SSL_HEADER`: comma-separated header/value pair, for example `HTTP_X_FORWARDED_PROTO,https`.
- `DJANGO_USE_X_FORWARDED_HOST`: boolean (`1`, `true`, `yes`, or `on`) when the trusted proxy should define the external host.
- `DJANGO_SESSION_COOKIE_SECURE` and `DJANGO_CSRF_COOKIE_SECURE`: booleans for HTTPS-only cookies behind the protected external hostname.
- `DJANGO_SESSION_COOKIE_PATH` and `DJANGO_CSRF_COOKIE_PATH`: optional cookie paths; default remains `/`.
- `DJANGO_STATIC_ROOT`: optional collectstatic/build output directory. The control-plane image sets this to `/app/staticfiles` and runs `collectstatic` at build time.

The control-plane image includes WhiteNoise so collected Django admin assets can be served by the control-plane process. Downstream nginx deployments should still expose only a scoped admin static path such as `<management-host>/static/admin/...`; do not broad expose `/static/` or general admin access. A production management hostname still requires an external access-control policy, a scoped static serving route, and an owner-approved private-runtime gate before being enabled.

The release candidate Worker image must contain the safe demo engine assets used by the catalog:

- `/app/engines/k6/target_apps_echo_smoke.js`
- `/app/engines/k6/lib/execution.js`
- `/app/engines/jmeter/target_apps_echo_latency_plan.jmx`

The catalog `script_path` values remain `engines/k6/target_apps_echo_smoke.js` and `engines/jmeter/target_apps_echo_latency_plan.jmx`; the Worker resolves them under `/app/`. The compose-oriented safe demo target URL is `http://echo-api:8000`. Single-host compose deployment must attach Worker and the local target service to a shared network where `echo-api` resolves. Split-host deployment must provide a routable target address through a future explicit deployment profile rather than overriding the controlled demo task request.

Core dispatch calls the Worker by the registered `WorkerNode.ip_address` and `port`. Since the current registry stores an IP address, single-host compose should let Worker register a reachable container IP on the shared Core/Worker network. For split-host deployment, set `WORKER_ADVERTISE_IP` to a Core-routable IP. Do not use manual `docker network connect` as the normal deployment smoke procedure; put shared networks or routable addresses in compose/runtime configuration.

The expected smoke progression is `pending -> dispatched -> running -> completed` for successful execution, or `pending -> dispatched -> running -> failed` with a diagnostic when the engine or target check fails. `POST /api/tasks/{id}/results/` remains a protected worker callback; unauthenticated external requests must still receive 403.

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
