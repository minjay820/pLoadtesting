# Specifications

This area is for implementation-facing contracts: APIs, data models, worker protocols, engine contracts, configuration schemas, and behavior that code must satisfy.

## Current Active Specs

- [External API v1 planning spec](external-api-v1.md)
- [API token access planning spec](api-token-auth.md)
- [Dashboard read model](dashboard-read-model.md)
- [API consumer guide](api-consumer-guide.md)
- [Task execution model](task-execution-model.md)
- [Distributed agent execution](distributed-agent-execution.md)
- [API example payloads](examples/)

## Likely Future Specs

- Worker Agent heartbeat, execution, distributed claim, and result callback contract.
- k6 script contract and output parsing expectations.
- JMeter plan and JTL parsing contract.
- Docker Compose service contract and environment variables.
- Observability metric names and retention expectations.

## Legacy Sources To Review

- `control-plane/ARCHITECTURE.md`
- `docs/architecture-interaction.md`
- `docs/k6-smoke-test-guide.md`
- `docs/local-validation-guide.md`
- `docs/observability-guide.md`
- `engines/k6/README.md`
- `engines/jmeter/README.md`

Mirror legacy material into `docs/v3/legacy/` before normalizing it here.
