# Local Smoke Image Build

This runbook builds local smoke images for compatible external client deployment validation. It does not push registry images and does not change runtime behavior.

## Purpose

Build the local image tags expected by downstream deployment packs:

- `local/ploadtesting-control-plane:0.1.0-rc.1`
- `local/ploadtesting-worker:0.1.0-rc.1`
- `local/ploadtesting-target-apps:0.1.0-rc.1`

These images are for runtime smoke and deployment validation. Registry publishing is a separate release step.

## Prerequisites

- Docker is available.
- Docker Compose is available for target-app smoke validation.
- Run from the repository root.
- Do not include live `.env*` files in build contexts.
- Do not push registry images as part of this runbook.

## Build Context Inventory

| Image | Build Context | Dockerfile | Status |
| --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `control-plane/` | `control-plane/Dockerfile` | buildable |
| `local/ploadtesting-worker:0.1.0-rc.1` | `workers/` | `workers/Dockerfile` | buildable |
| `local/ploadtesting-target-apps:0.1.0-rc.1` | `target-apps/` | `target-apps/Dockerfile` | buildable |

Each context has a `.dockerignore` that excludes live env files, Python cache files, local venvs, and generated artifacts.

## Build Commands

```bash
docker build -t local/ploadtesting-control-plane:0.1.0-rc.1 control-plane
docker build -t local/ploadtesting-worker:0.1.0-rc.1 workers
docker build -t local/ploadtesting-target-apps:0.1.0-rc.1 target-apps
```

## Control Plane Runtime Smoke

The control-plane image is expected to start the Django API server by default:

```text
python manage.py runserver 0.0.0.0:8000
```

The image exposes port `8000` for local deployment smoke. The default command does not run migrations automatically; schema preparation remains an explicit operator step so deployment packs can choose the correct database lifecycle for their environment.

External database environment variables are supplied by the deployment pack or host runtime. Do not bake runtime-only values into the image, and do not require live `.env*` files in the build context.

For PostgreSQL runtime settings, the control-plane image reads `PLOADTESTING_DATABASE_URL` first, then `DATABASE_URL`, then falls back to local sqlite when neither variable is present. PostgreSQL schema selection should be supplied with `PGOPTIONS`, for example `-c search_path=plt,public`; `PLOADTESTING_DB_SCHEMA` is also accepted when it matches the safe identifier pattern documented in [External database runtime](external-db-runtime.md).

The control-plane image must expose a read-only catalog for deployment smoke without requiring external database seed data. `GET /api/tasks/templates/` and `GET /api/tasks/templates/coverage/` read registry/static profile definitions. Because this image is built with `control-plane/` as its Docker context, the runtime can fall back to bundled safe demo profile definitions under `apps/tasks/catalog/` when repo-root `target-apps` catalog files are not present.

Deployment smoke should use safe demo profiles only for short local validation. It must not run long tests or target third-party services.

To enable controlled task operation smoke in the control-plane image, set the disabled-by-default flag:

```text
PLOADTESTING_ENABLE_DEMO_TASK_API=true
```

With the flag enabled, compatible external clients can submit only the bundled safe demo profiles and can read only smoke-created task metadata. Core attempts one immediate worker dispatch after task creation. If no compatible idle worker is registered, the task remains `pending` with a diagnostic `error_message`; if a compatible worker accepts the task, the task moves to `dispatched` and later transitions depend on the protected worker result callback. Result callbacks and artifact download remain protected for unauthenticated external requests.

Non-sharded safe demo tasks return a normal shard read model with `mode=single`, `shards=[]`, and `status=not_applicable`; clients should not treat that response as degraded.

Bounded local container smoke:

```bash
docker run --rm -d \
  --name ploadtesting-control-plane-smoke \
  -p 18000:8000 \
  local/ploadtesting-control-plane:0.1.0-rc.1

docker ps --filter name=ploadtesting-control-plane-smoke
docker logs --tail=80 ploadtesting-control-plane-smoke
curl -i http://localhost:18000/api/tasks/templates/
docker stop ploadtesting-control-plane-smoke
```

Bounded demo task API smoke:

```bash
docker run --rm -d \
  --name ploadtesting-control-plane-demo-api-smoke \
  -e PLOADTESTING_ENABLE_DEMO_TASK_API=true \
  -p 18000:8000 \
  local/ploadtesting-control-plane:0.1.0-rc.1

curl -fsS http://localhost:18000/api/tasks/templates/
curl -fsS http://localhost:18000/api/tasks/templates/coverage/
docker stop ploadtesting-control-plane-demo-api-smoke
```

This phase performs no registry push.

## Inspect Commands

```bash
docker image inspect local/ploadtesting-control-plane:0.1.0-rc.1
docker image inspect local/ploadtesting-worker:0.1.0-rc.1
docker image inspect local/ploadtesting-target-apps:0.1.0-rc.1
```

Compact inspect output:

```bash
docker image inspect \
  local/ploadtesting-control-plane:0.1.0-rc.1 \
  local/ploadtesting-worker:0.1.0-rc.1 \
  local/ploadtesting-target-apps:0.1.0-rc.1 \
  --format '{{.RepoTags}}|{{.Id}}|{{.Created}}|{{.Size}}|{{json .RepoDigests}}'
```

## 2026-06-16 Local Build Record

| Image Tag | Image ID / Digest | Created | Size |
| --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:5629c480c21156c71aa7cb08590f3c27ca46df251844890efb879fcd2d620443` | `2026-06-16T08:43:35.23029021Z` | `71904271` |
| `local/ploadtesting-worker:0.1.0-rc.1` | `sha256:8700a6f9807c20809b43851e1bfc97643807b4567da97876fb2f110343650b43` | `2026-06-16T08:43:34.776078418Z` | `335272297` |
| `local/ploadtesting-target-apps:0.1.0-rc.1` | `sha256:440bd2e724059127b0b8a59d9fc84cf76b20de542a7b9d41ccb2975cd1d0798e` | `2026-06-15T14:30:20.239281752Z` | `62586146` |

Repo digests were available for the local tags after build.

Resolved local repo digests:

- `local/ploadtesting-control-plane@sha256:5629c480c21156c71aa7cb08590f3c27ca46df251844890efb879fcd2d620443`
- `local/ploadtesting-worker@sha256:8700a6f9807c20809b43851e1bfc97643807b4567da97876fb2f110343650b43`
- `local/ploadtesting-target-apps@sha256:440bd2e724059127b0b8a59d9fc84cf76b20de542a7b9d41ccb2975cd1d0798e`

## 2026-06-19 Control Plane Entrypoint Build Record

| Image Tag | Image ID / Digest | Created | Size | CMD | Entrypoint |
| --- | --- | --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:41feb6f181371672b117291ae72887da6651ccc5b01b379d8e7d8ecabf66483d` | `2026-06-19T01:40:11.88186796Z` | `71904707` | `["python","manage.py","runserver","0.0.0.0:8000"]` | `null` |

Container smoke started the image with port `18000:8000`. Django reported `System check identified no issues`, served at `http://0.0.0.0:8000/`, and returned an API JSON response from `GET /api/tasks/templates/`. The response was an expected access-control response because no runtime access header was supplied for this bounded smoke.

## 2026-06-19 PostgreSQL Runtime Build Record

| Image Tag | Image ID / Digest | Created | Size | CMD |
| --- | --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:9671221ca9a9566b90ed138e6c7f2c4bbc2407947eeb682148652adb5555524e` | `2026-06-19T05:54:43.980209416Z` | `79466309` | `["python","manage.py","runserver","0.0.0.0:8000"]` |

Driver smoke passed with `import psycopg`. Placeholder PostgreSQL runtime env selected `django.db.backends.postgresql`, and `python manage.py check` passed in the rebuilt image without running migrations.

## 2026-06-19 Safe Demo Catalog Build Record

| Image Tag | Image ID / Digest | Created | Size | CMD |
| --- | --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:97819fbf5b57b5262ba9238be4aadd06b89c6dbaf2432c97a90999a42a954450` | `2026-06-19T06:30:29.133051715Z` | `79469880` | `["python","manage.py","runserver","0.0.0.0:8000"]` |

Image catalog smoke confirmed that the control-plane image exposes the bundled safe demo fallback catalog when repo-root `target-apps` catalog files are not present in the image context:

- `GET /api/tasks/templates/`: HTTP 200, `templates` envelope, 1 target, 2 profiles.
- `GET /api/tasks/templates/coverage/`: HTTP 200, `summary/targets/profiles/gaps` envelope, `target_app_count=1`, `profile_count=2`, `exact_coverage_profile_count=2`, `gap_profile_count=0`.

## 2026-06-19 Controlled Demo Task API Build Record

| Image Tag | Image ID / Digest | Created | Size | CMD |
| --- | --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:458afb6e69b1a65b745db05d0f006f7484ea76e08cea87adaa5a40d3f20262f7` | `2026-06-19T07:22:20.068954877Z` | `79478767` | `["python","manage.py","runserver","0.0.0.0:8000"]` |

Bounded container smoke with `PLOADTESTING_ENABLE_DEMO_TASK_API=true` confirmed:

- `GET /api/tasks/templates/`: HTTP 200, 2 profiles in the image fallback catalog.
- `GET /api/tasks/templates/coverage/`: HTTP 200, `profile_count=2`.
- `POST /api/tasks/` with `echo-api` / `echo-k6-smoke`: HTTP 201 and task id returned.
- Task detail, result summary, and artifact metadata: HTTP 200 for the smoke-created task.
- Shard-plan: HTTP 404 no-plan response for the smoke-created task without distribution metadata.
- Artifact download and result callback: HTTP 403 without broader access.

## 2026-06-19 Demo Task Dispatch Smoke Build Record

| Image Tag | Image ID / Digest | Created | Size | CMD |
| --- | --- | --- | --- | --- |
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:e9077134eefea42d042f9016888d8378588316f04d7138c9ba7df4bea6c3b006` | `2026-06-19T07:50:24.521195587Z` | `79480716` | `["python","manage.py","runserver","0.0.0.0:8000"]` |

Bounded container smoke with `PLOADTESTING_ENABLE_DEMO_TASK_API=true` confirmed:

- `GET /api/tasks/templates/`: HTTP 200, 2 profiles in the image fallback catalog.
- `GET /api/tasks/templates/coverage/`: HTTP 200, `profile_count=2`.
- `POST /api/tasks/` with `echo-api` / `echo-k6-smoke`: HTTP 201 and task id returned.
- With no registered compatible worker in the bounded container, task status remained `pending` with a dispatch diagnostic.
- Task detail: HTTP 200.
- Shard-plan: HTTP 200, `mode=single`, `status=not_applicable`.
- Result summary: HTTP 200, `status=not_available`.
- Artifact metadata: HTTP 200, 5 planned artifacts.
- Artifact download and result callback: HTTP 403 without broader access.

## Cleanup

Remove local smoke images only when they are no longer needed:

```bash
docker image rm local/ploadtesting-control-plane:0.1.0-rc.1
docker image rm local/ploadtesting-worker:0.1.0-rc.1
docker image rm local/ploadtesting-target-apps:0.1.0-rc.1
```

## External Deployment Pack Usage

Compatible external client deployment packs can consume these local tags by setting their image env values to the `local/...:0.1.0-rc.1` names above.

The deployment pack consumes image references only. It does not require source vendoring and should interact with Core through HTTP APIs and documented contracts.

## Limitations

- No registry push is performed.
- No artifact download is implemented.
- No report viewer is implemented.
- No scheduler, access-control runtime, or database migration is changed.
- Target-app behavior is not changed.
