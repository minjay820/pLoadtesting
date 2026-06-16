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
| `local/ploadtesting-control-plane:0.1.0-rc.1` | `sha256:ebf4623a1707430069f1e491fb5b6289a9b9f8b03796638f09dfb1dcfa6d71b1` | `2026-06-16T08:31:41.741366504Z` | `101348919` |
| `local/ploadtesting-worker:0.1.0-rc.1` | `sha256:b4944440555fe1da820ba901f4b96dcca1b1d9af0dd6cc88ca78aa2de136a1c1` | `2026-06-16T02:22:34.271926046Z` | `335290564` |
| `local/ploadtesting-target-apps:0.1.0-rc.1` | `sha256:606626b5414aad58ce79a2e81fac563b192ffe516251c25e5a331543acd7c7f7` | `2026-06-15T14:30:20.239281752Z` | `62586146` |

Repo digests were available for the local tags after build.

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
- No scheduler, token system, or database migration is changed.
- Target-app behavior is not changed.
