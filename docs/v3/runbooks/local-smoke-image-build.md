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
