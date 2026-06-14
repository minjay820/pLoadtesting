# API Token Access Planning Spec

This spec defines a future scoped API access model for pLoadtesting. It does not implement the model and does not replace the current shared preview setting in this phase.

## Current Baseline

The Control Plane currently uses `PLOADTESTING_API_TOKEN` through a shared-token DRF permission. Clients may send the value through either:

- `Authorization: Bearer ...`
- `X-PLOADTESTING-API-TOKEN: ...`

The Worker Agent uses the same preview access value when registering, sending heartbeats, receiving dispatch, and posting results.

This is acceptable for local and controlled preview deployments, but it is not sufficient for production-grade scoped access.

## Goals

- Replace all-or-nothing preview access with scoped API access.
- Support separate access for dashboard users, automation clients, Worker Agents, and administrators.
- Preserve a migration path for existing local deployments.
- Avoid storing raw access values in logs or response payloads.
- Keep worker callback and dashboard/user-facing actions separated.

## Planned Scopes

| Scope | Purpose |
|---|---|
| `tasks:read` | List and inspect tasks |
| `tasks:write` | Create and cancel tasks |
| `templates:read` | Read manifest-driven target profile catalog |
| `workers:read` | List and inspect Worker Agent state |
| `workers:write` | Register workers and send heartbeats |
| `results:write` | Submit task results from Worker Agents |
| `results:read` | Read task result summaries |
| `tokens:admin` | Create, rotate, revoke, and inspect token metadata |

## Suggested Actor Profiles

| Actor | Minimum Scopes |
|---|---|
| Dashboard read-only user | `tasks:read`, `templates:read`, `workers:read`, `results:read` |
| Dashboard operator | dashboard read-only scopes plus `tasks:write` |
| Worker Agent | `workers:write`, `results:write` |
| Automation client | `tasks:read`, `tasks:write`, `templates:read`, `results:read` |
| Access administrator | `tokens:admin` plus audit read scopes |

## Token Lifecycle

A future implementation should support:

- create scoped access value
- show the raw value only once at creation time
- store only a hash or derived verifier
- rotate by creating a new value before revoking the old one
- revoke immediately
- record last-used timestamp and scope metadata
- optionally set expiration timestamp

## Migration Path

1. Keep `PLOADTESTING_API_TOKEN` as preview compatibility.
2. Add scoped token storage and verification behind the same header patterns.
3. Prefer scoped access when a stored token matches.
4. Keep shared preview access available only when explicitly configured.
5. Document a removal or disable-by-default milestone after dashboard/API consumers are migrated.

## Enforcement Model

Future API views should declare required scopes by route family:

- task list/detail requires `tasks:read`
- task create requires `tasks:write`
- template list requires `templates:read`
- worker list requires `workers:read`
- worker registration/heartbeat requires `workers:write`
- result callback requires `results:write`

The Worker `/execute` endpoint should continue to require a value accepted by the Worker Agent. For distributed deployments, Control Plane to Worker dispatch access should be configured independently from user-facing dashboard access.

## Non-Goals For This Planning Round

- No database model changes.
- No new permission classes.
- No token creation endpoint.
- No dashboard login flow.
- No external identity provider integration.

## Safety Notes

- Documentation examples must use placeholders, not real deployment values.
- Access values must not be printed in logs, issue drafts, or test output.
- Revocation and rotation should be testable before any public deployment recommendation is made.
