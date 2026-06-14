# Distributed Deployment Runbook

This runbook describes a future three-host pLoadtesting deployment for controlled internal networks. It is an operational planning document, not a production hardening guarantee.

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
| Task dispatch | Control Plane to Worker | `POST /execute` |
| Result callback | Worker to Control Plane | `POST /api/tasks/{id}/results/` |
| Load generation | Worker to target app | k6/JMeter traffic |
| Dashboard/API user | User network to Control Plane | task, worker, template, and result inspection |

The Control Plane must be able to reach each Worker's advertised `ip_address` and `port`. Each Worker must be able to reach the Control Plane base URL.

## Preflight Checklist

- Host clocks are synchronized.
- Control Plane can resolve and connect to every Worker Agent address.
- Each Worker can resolve and connect to the Control Plane URL.
- Workers can reach only the intended target app networks.
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
| Result missing | Worker can reach Control Plane result callback route |
| Load traffic fails | Worker can reach the authorized target URL |

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
