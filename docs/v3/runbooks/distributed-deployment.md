# Distributed Deployment Runbook

This runbook describes a future three-host pLoadtesting deployment for controlled internal networks. It is an operational planning document, not a production hardening guarantee.

The current preview runtime uses Control Plane push dispatch to a Worker Agent `/execute` endpoint. Phase 5.9 adds manual shard distribution metadata and shard execution plan export, but it does not add full distributed scheduling. The future distributed execution model should move toward agent claim, where Worker Agents connect to the Control Plane to claim shard work.

## Deployment Model

| Host | Services | Responsibility |
|---|---|---|
| Host A | Control Plane web, Control Plane Celery, Redis, optional InfluxDB/Grafana | API, scheduler, dispatch, result storage, observability |
| Host B | Worker Agent | k6 and JMeter execution |
| Host C | Worker Agent | additional k6 and JMeter execution capacity |

Target apps should run either:

- on the same internal network as the workers, or
- as explicitly authorized internal targets owned by the operator.

Do not use this system against third-party targets or systems without explicit permission.

## Network Direction

| Flow | Direction | Purpose |
|---|---|---|
| Worker registration | Worker to Control Plane | `POST /api/workers/` |
| Worker heartbeat | Worker to Control Plane | `POST /api/workers/{id}/heartbeat/` |
| Current preview task dispatch | Control Plane to Worker | `POST /execute` |
| Manual shard plan read | User network to Control Plane | `GET /api/tasks/{id}/shard-plan/` |
| Run history read | User network to Control Plane | `GET /api/tasks/` |
| Result summary read | User network to Control Plane | `GET /api/tasks/{id}/result-summary/` |
| Artifact metadata read | User network to Control Plane | `GET /api/tasks/{id}/artifacts/` |
| Future shard claim | Worker to Control Plane | Claim pending shard work for a matching agent selector |
| Result callback | Worker to Control Plane | `POST /api/tasks/{id}/results/` |
| Load generation | Worker to target app | k6/JMeter traffic |
| Dashboard/API user | User network to Control Plane | task, worker, template, and result inspection |

The Control Plane must be able to reach each Worker's advertised `ip_address` and `port`. Each Worker must be able to reach the Control Plane base URL.

In the current manual shard metadata MVP, the Control Plane still uses the existing push dispatch flow. In the future agent-claim model, the Control Plane does not need to initiate HTTP requests to each agent for normal execution. Workers still need outbound connectivity to the Control Plane for registration, heartbeat, claim, artifact metadata, and result shard submission. Target apps do not need to connect to the Control Plane.

## Preflight Checklist

- Host clocks are synchronized.
- For current preview dispatch, Control Plane can resolve and connect to every Worker Agent address.
- For future agent claim, each Worker can claim work from the Control Plane without requiring inbound agent reachability from the Control Plane.
- Each Worker can resolve and connect to the Control Plane URL.
- Workers can reach only the intended target app networks.
- Worker labels state target network reachability, such as `target_network=internal-a`.
- Redis is reachable from Control Plane web and Celery services.
- The same configured preview access value or future scoped access is aligned between Control Plane and Worker Agents.
- Worker hosts have k6 and JMeter installed through the Worker image or runtime environment.
- Ports are not exposed publicly unless protected by network controls and access enforcement.

## Suggested Port Responsibilities

| Port | Component | Exposure |
|---|---|---|
| `9000` | Control Plane web | internal operator/API network |
| `8100` | Worker Agent | Control Plane only |
| `6379` | Redis | Control Plane service network only |
| `8086` | InfluxDB | internal observability network only |
| `3000` | Grafana | internal observability network only |
| target app ports | target apps | Worker networks only unless intentionally exposed |

## Startup Sequence

1. Start Redis and Control Plane services on Host A.
2. Run Control Plane checks and migrations according to the active deployment procedure.
3. Start observability services if they are part of the deployment.
4. Start Worker Agent on Host B with `CONTROL_PLANE_URL` pointing to Host A.
5. Start Worker Agent on Host C with the same Control Plane URL and a unique worker name.
6. Confirm both workers appear in `GET /api/workers/`.
7. Submit a low-cost template-driven smoke task.
8. Confirm task dispatch, result callback, and worker heartbeat remain stable.
9. Submit a manual-shard metadata task and confirm `GET /api/tasks/{id}/shard-plan/` returns the expected shard rows.
10. For future distributed execution, confirm shard claim, result shard collection, and aggregate status after those runtime features are implemented.

## Validation Commands

Use placeholders for hostnames and access values:

```bash
curl -fsS http://CONTROL_PLANE_HOST:9000/api/workers/
curl -fsS http://WORKER_HOST_B:8100/execute
curl -fsS http://WORKER_HOST_C:8100/execute
```

The Worker `/execute` endpoint expects an authenticated POST request for real dispatch. A simple GET may return a method error and still confirm routing to the service. Use an authenticated, low-cost task submission through the Control Plane for end-to-end validation.

## Failure Checks

| Symptom | Check |
|---|---|
| Worker does not appear | Worker can resolve Control Plane URL and access value is aligned |
| Worker appears offline | heartbeat route reachable and host clocks are synchronized |
| Task remains pending | worker is online, idle, and advertises the task engine capability |
| Dispatch fails | Control Plane can reach Worker `/execute` on advertised address |
| Shard plan missing | task was created with a valid `distribution` object |
| Future shard remains unclaimed | agent labels, engine capability, and target network selector match the shard |
| Result missing | Worker can reach Control Plane result callback route |
| Result summary not available | task has not posted a `TestResult`; handle `not_available` as a normal lifecycle state |
| Artifact metadata empty | artifact metadata storage is not implemented; placeholder response is expected |
| Partial success | inspect failed, cancelled, timed-out, and completed shard counts separately |
| Load traffic fails | Worker can reach the authorized target URL |

## Duration And Stop Policy Checks

For future duration-based execution:

- Confirm `duration_seconds`, `graceful_stop_seconds`, and `max_run_seconds` are present in the submitted task contract.
- Confirm a 1-hour task stops new traffic at 1 hour and only waits for in-flight requests during the configured grace period.
- Confirm worker-level timeout is longer than the requested duration plus ramp and grace time.
- Confirm forced stops are recorded in result metadata instead of appearing as ordinary successful completion.

## Dataset Partition Checks

For current manual shard dataset partition metadata:

- Confirm every shard has a stable `shard_id`.
- Confirm every shard uses `artifact://` or `inline://` dataset source.
- Confirm a 5000-row dataset can be represented as offset 0 limit 2000 and offset 2000 limit 3000.
- Confirm worker test payloads pass one selected shard to k6 or JMeter as engine metadata.
- Treat actual dataset loading, overlap detection, retries, and attempt numbers as future work.

## Result Aggregation Checks

For distributed results:

- Sum total requests and failed requests across result shards.
- Recalculate error rate from summed totals.
- Recalculate throughput from the overall run time window.
- Do not average shard p95 or p99 values into a global percentile.
- Mark global latency percentiles unavailable until raw samples, histogram buckets, HDR histogram, t-digest, or engine-supported merge output is available.
- Read `GET /api/tasks/{id}/result-summary/` for task-level summaries and do not infer missing percentile fields.
- Read `GET /api/tasks/{id}/artifacts/` for artifact metadata; current placeholder responses do not imply downloadable files.

## Rollback

1. Stop new task submission.
2. Mark affected workers draining or stop Worker Agent processes.
3. Wait for active tasks to complete or fail cleanly.
4. Stop Control Plane Celery scheduling if dispatch must pause.
5. Restore previous compose/runtime configuration.
6. Restart services in the previous known-good topology.
7. Run a low-cost smoke task before resuming normal usage.

## Hardening Before Production Use

- Replace shared preview access with scoped API access.
- Restrict network paths so workers can only reach approved target networks.
- Add TLS termination and trusted host configuration.
- Add log redaction for access headers and sensitive runtime parameters.
- Define backup and retention policies for task results and observability data.
- Add deployment-specific monitoring for worker heartbeat age, task failure rate, and dispatch errors.
- Add monitoring for unclaimed shards, shard retries, partial success, forced stops, and aggregation quality.
