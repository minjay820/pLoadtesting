# Repository Publication Policy

This document defines the planned GitLab-private and GitHub-public publication model for pLoadtesting. It is a planning contract, not a record that the remotes have already been changed.

## Purpose

The target workflow is to keep GitLab as the private working area that preserves full source, full history, private branches, validation evidence, and internal issue context. GitHub is the public release and collaboration surface for content that is intentionally approved for publication.

The policy avoids a bidirectional mirror. A mirror is only appropriate when both sides should receive the same refs, files, and history.

## Source Of Truth

GitLab is the private authority after the workflow is adopted:

- `gitlab/main` is the private integration branch and should contain the full project history.
- `gitlab/feature/*`, `gitlab/fix/*`, `gitlab/docs/*`, and similar topic branches are private development branches unless explicitly exported.
- `gitlab/release/*` branches are private release-candidate branches that retain full validation context.
- GitLab tags can include internal release candidates such as `vX.Y.Z-rc.N` or deployment-only checkpoints.
- GitLab merge requests and GitLab issues are the primary system for private implementation planning, internal blockers, and validation evidence.

GitHub is the public surface:

- `origin/main` should contain only the approved public tree.
- `origin/release/*` is optional and should be used only for public release preparation.
- Public `vX.Y.Z` tags should be pushed only after release export validation passes.
- GitHub pull requests can be used for public review and public release merging.
- GitHub issues are for public bug reports, feature requests, documentation feedback, and external collaboration.
- GitHub Container Registry (`ghcr.io`) is the planned public image surface for `ploadtesting-control-plane`, `ploadtesting-worker`, and `ploadtesting-target-apps`.

## Public Export Boundary

The GitHub public tree must be generated from an allowlist, not by pushing the private GitLab repository directly.

Always-public candidates:

- `README.md`
- `LICENSE`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `ROADMAP.md`
- `SECURITY.md`
- `THIRD_PARTY_NOTICES.md`
- `.github/ISSUE_TEMPLATE/`
- `.github/pull_request_template.md`
- Selected `docs/v3/` documents that do not disclose private infrastructure, credentials, customer data, or internal deployment details.

Conditionally-public candidates:

- `.github/workflows/` when the workflow is suitable for public CI.
- `.github/workflows/publish-ghcr.yml` when container publication is intended for GitHub Container Registry.
- `control-plane/`, `workers/`, `target-app/`, `target-apps/`, `engines/`, and compose files only when the release is intentionally an OSS code release and the exported tree has passed validation.
- `docs/v3/runbooks/` only when the runbook describes public setup or release validation without private hostnames, tokens, internal network names, or operator-only deployment details.

Never-public candidates:

- `.env*` files and local secret files.
- Local databases, generated artifacts, reports, logs, coverage output, and runtime state.
- Private deployment manifests, private hostnames, private registry details, credentials, tokens, customer data, or internal incident notes.
- GitLab-only planning notes that expose internal priorities or non-public implementation details.

## Release Export Verification

Before pushing anything to GitHub:

1. Start from a named GitLab commit or release branch.
2. Confirm the GitLab worktree is clean or explicitly record the uncommitted exception.
3. Run the relevant GitLab validation set for the release scope.
4. Generate the GitHub public tree in a temporary worktree or export directory from the allowlist.
5. Verify that the public tree contains only approved paths.
6. Run a secret and private-context scan over the public tree.
7. Run `git diff --check` on the public export.
8. Run the public validation set that GitHub users should be able to reproduce.
9. Push the public export to a GitHub branch and open a GitHub pull request when review is needed.
10. Push the public `vX.Y.Z` tag only after GitHub CI and release review pass.

Validation evidence should record:

- GitLab source commit SHA.
- Export allowlist version or script commit SHA.
- Public GitHub branch or tag.
- Test commands and results.
- Any intentionally omitted private paths.

## Issue Ownership

GitLab is the primary issue system for:

- Private roadmap planning.
- Internal implementation tasks.
- Private validation blockers.
- Deployment or infrastructure work that references private hosts, credentials, or operator context.

GitHub is the primary issue system for:

- Public bugs.
- Public feature requests.
- Public documentation requests.
- External contributor discussion.
- Release notes and public follow-up tasks.

When the same work has private and public parts, create one private GitLab issue as the implementation authority and one GitHub issue only for the public-facing part. The GitHub issue may reference an internal tracking ID only if it does not disclose private details.

## Complexity Budget

This workflow stays manageable if it has one private authority, one public export path, and one release gate.

Avoid:

- Bidirectional issue ownership.
- Manually cherry-picking many unrelated commits into GitHub.
- Pushing private branches directly to GitHub.
- Treating GitHub as a partial mirror without an explicit allowlist.

Prefer:

- A repeatable export script or checklist.
- A small public allowlist.
- Release branches only when needed.
- GitLab CI for private validation and GitHub Actions for public reproducibility.

## GHCR Image Publication

The public image publication path should publish these package names to GitHub Container Registry:

- `ghcr.io/<owner>/ploadtesting-control-plane`
- `ghcr.io/<owner>/ploadtesting-worker`
- `ghcr.io/<owner>/ploadtesting-target-apps`

The tracked workflow entrypoint is `.github/workflows/publish-ghcr.yml`.

Current workflow behavior:

- manual `workflow_dispatch`
- separate tag inputs for control-plane, worker, and target-apps images
- optional `latest` alias publication
- multi-architecture build for `linux/amd64` and `linux/arm64`
- package publish through the repository `GITHUB_TOKEN`

Publication rules:

- use OCI labels that point back to the source repository so packages can be linked cleanly to the public repo
- verify package visibility and linked-repository settings in the GitHub Packages UI after the first push
- keep registry credentials out of tracked env files; deployment hosts should authenticate with `docker login` or a dedicated automation token
- do not treat package publication as deployment approval by itself

## Current-State Note

As of 2026-06-20, the local repository still tracks GitHub `origin/main` as the day-to-day upstream and has a separate `gitlab` remote. Adopting this policy requires a deliberate later transition of branch tracking, release export mechanics, and issue ownership. This document does not make that transition by itself.
