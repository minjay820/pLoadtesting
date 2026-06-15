# pLoadtesting Core Boundary

This document defines the Core responsibility boundary for public project governance, external clients, downstream integrations, compatible dashboards, and operational clients.

## Core Mission

pLoadtesting Core provides a neutral load testing foundation: target app profiles, task templates, Control Plane APIs, worker execution, engine assets, coverage metadata, task execution metadata, manual shard metadata, and result contracts.

Core should remain reusable by multiple API consumers. It should not contain client-specific assumptions, client-specific product language, or dependencies on a particular external dashboard or integration layer.

## What Core Provides

- Local target app catalog and profile metadata.
- k6 and JMeter profile parity metadata.
- Preview Control Plane APIs for workers, tasks, templates, coverage, results, execution metadata, and shard plan export.
- Worker runtime support for duration execution metadata and one-shard dataset metadata mapping.
- Documentation contracts for task execution, distributed metadata, API consumption, and dashboard read models.
- Public project governance under `docs/v3/`.

## What Core Intentionally Does Not Provide

- A complete dashboard UI.
- A scoped token system beyond the current preview compatibility layer.
- A full distributed scheduler or worker claim lifecycle.
- Persistent shard tables or per-shard result rows.
- Dataset loading, dataset resolver, or artifact storage lifecycle.
- Exact percentile merge across shards.
- Client-specific integration logic.

## External Client Responsibilities

External clients are responsible for:

- Calling documented HTTP APIs.
- Handling preview API compatibility boundaries.
- Ignoring unknown additive fields.
- Presenting user workflows such as create-task forms or dashboard views.
- Storing client-specific state outside Core unless Core documents a generic storage contract.
- Translating client needs into generic Core capability requests.

## Downstream Integration Responsibilities

Downstream integrations are responsible for:

- Keeping integration-layer assumptions out of Core.
- Using template identifiers and coverage metadata instead of reading internal files directly.
- Handling authentication, deployment, and network boundaries appropriate to their environment.
- Treating planning-only Core documents as roadmap direction, not runtime availability.
- Reporting compatibility gaps as neutral Core issues.

## Extension-Friendly Design

Core extension points should be generic:

- New target profiles should appear through template metadata.
- New execution controls should extend the `execution` object with documented validation.
- New shard behavior should extend `distribution` and shard plan contracts.
- New result behavior should extend result and aggregation contracts.
- New client needs should be expressed through reusable API fields or endpoints.

## Anti-Coupling Rules

- Do not reference or depend on a specific external client implementation from Core.
- Do not add client-specific branches to Control Plane, worker, engine, or target app code.
- Do not require external clients to import internal Python functions.
- Do not expose undocumented storage layout as a public integration surface.
- Do not describe future capabilities as runtime-supported until they are implemented and validated.
- Do not encode integration-layer policy into Core when a generic API contract can represent it.

## Decision Table

| Capability | Core Responsibility | External Client Responsibility | Notes |
|---|---|---|---|
| Template catalog | Provide `GET /api/tasks/templates/` with documented profile metadata. | Render selectable profiles and tolerate additive fields. | Stable candidate. |
| Coverage metadata | Provide `GET /api/tasks/templates/coverage/` with summary, target, profile, and gap rows. | Build coverage views and validate expected profile parity. | Stable candidate. |
| Task creation | Accept documented task creation payloads. | Prefer `target_app_id` and `target_profile_id` over direct script entry. | Preview `/api/` now; future `/api/v1` should stabilize. |
| Execution metadata | Validate and store `execution`, then map it to supported engines. | Provide duration and stop settings only through documented fields. | Experimental runtime contract. |
| Distribution metadata | Validate and store manual shard metadata and generate shard plans. | Build manual shard forms and preview intended assignment. | Experimental runtime contract. |
| Shard scheduling | Document future lifecycle concepts. | Do not assume Core fans out shards today. | Future work. |
| Dataset partition | Validate dataset source, format, offset, and limit metadata. | Own dataset preparation and source references. | Runtime metadata only; no dataset loading yet. |
| Result aggregation | Define summary-only placeholder and aggregation rules. | Avoid direct averaging of latency averages or percentiles. | Exact percentile merge is future work. |
| Dashboard UI | Provide API and read-model contracts. | Implement UI, navigation, filters, and user workflows. | Core does not implement a dashboard in this phase. |
| Token access | Document planned scoped access model. | Use current preview access mechanism where applicable. | Scoped token API is planning-only. |
| Artifact handling | Validate placeholder-safe dataset source conventions. | Manage artifact storage or references until Core provides an artifact API. | Full artifact browser API is planning-only. |

## Boundary Decision Rule

If a requested change benefits only one integration layer, first restate it as a generic Core capability. If it cannot be represented generically, keep it outside Core.
