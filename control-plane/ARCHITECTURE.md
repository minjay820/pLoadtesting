# 🖥️ Control Plane — Architecture Design Document

> **pLoadtesting · Control Plane MVP**
> Tech Stack: Python Django + Django REST Framework · SQLite (MVP) · Celery + Redis
> Document Version: 1.0.0 · Phase 4 Architecture Blueprint

---

## 1. System Positioning

The Control Plane is the "central nerve center" of the pLoadtesting ecosystem, responsible for:

1. **Task Management**: Receiving load test tasks created by users, selecting engine scripts, and managing target URLs.
2. **Worker Scheduling**: Dispatching tasks to available Worker nodes.
3. **Result Aggregation**: Collecting k6/JMeter JSON reports returned by Workers, parsing, and persisting them.
4. **Web UI Support**: Providing RESTful APIs for the frontend Dashboard.

```
┌─────────────────────────────────────────────────────────────┐
│                      Control Plane                          │
│                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  Django     │   │  Celery      │   │  Django REST    │  │
│  │  ORM        │──▶│  Task Queue  │   │  Framework API  │  │
│  │  (SQLite)   │   │  (Redis)     │   │  (HTTP/JSON)    │  │
│  └─────────────┘   └──────┬───────┘   └────────┬────────┘  │
└───────────────────────────┼────────────────────┼───────────┘
                            │ dispatch            │ REST API
                    ┌────────▼──────────┐   ┌─────▼──────┐
                    │  Worker Agent(s)  │   │  Web UI /  │
                    │  (Remote Node)    │   │  k6 CLI    │
                    └───────────────────┘   └────────────┘
```

---

## 2. Database Schema Design (Django Models)

### 2.1 `WorkerNode` — Remote Node Registry

Tracks remote Worker nodes registered with the Control Plane.

```python
class WorkerNode(models.Model):

    # ── Identity ──────────────────────────────────────────────────
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=128, unique=True)
    ip_address = models.GenericIPAddressField()
    port       = models.PositiveIntegerField(default=8100)

    # ── Status ────────────────────────────────────────────────────
    class Status(models.TextChoices):
        ONLINE   = 'online',   'Online'
        BUSY     = 'busy',     'Busy'
        OFFLINE  = 'offline',  'Offline'
        DRAINING = 'draining', 'Draining'

    status        = models.CharField(max_length=16, choices=Status.choices,
                                     default=Status.OFFLINE, db_index=True)
    # List of engines supported (JSON Array, e.g. ["k6", "jmeter"])
    capabilities  = models.JSONField(default=list)

    # ── Observability ──────────────────────────────────────────────
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    resource_snapshot = models.JSONField(default=dict, blank=True)
    active_task_count = models.PositiveIntegerField(default=0)

    # ── Audit ──────────────────────────────────────────────────────
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_heartbeat_at']

    def is_alive(self, timeout_seconds: int = 30) -> bool:
        if not self.last_heartbeat_at:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.last_heartbeat_at >= timezone.now() - timedelta(seconds=timeout_seconds)
```

**Fields Summary**

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | Unique identifier |
| `name` | CharField(128) | Unique node name |
| `ip_address` | GenericIPAddressField | IPv4 / IPv6 address |
| `port` | PositiveIntegerField | Worker Agent listen Port, default 8100 |
| `status` | CharField (Enum) | online / busy / offline / draining |
| `capabilities` | JSONField | e.g. `["k6", "jmeter"]` |
| `last_heartbeat_at` | DateTimeField | Last heartbeat timestamp |
| `resource_snapshot` | JSONField | e.g. `{"cpu_pct": 23.5, "mem_pct": 41.2}` |
| `active_task_count` | PositiveIntegerField | Running tasks count |
| `registered_at` | DateTimeField | Registration timestamp |
| `updated_at` | DateTimeField | Update timestamp |

---

### 2.2 `LoadTestTask` — Load Test Task

Represents a load testing task dispatched to a worker.

```python
class LoadTestTask(models.Model):

    # ── Identity ──────────────────────────────────────────────────
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=256)

    # ── Configuration ─────────────────────────────────────────────
    class Engine(models.TextChoices):
        K6         = 'k6',         'k6'
        JMETER     = 'jmeter',     'JMeter'
        LOADRUNNER = 'loadrunner', 'LoadRunner'

    engine      = models.CharField(max_length=16, choices=Engine.choices, db_index=True)
    script_path = models.CharField(max_length=512)
    parameters  = models.JSONField(default=dict, blank=True)

    # ── Target ────────────────────────────────────────────────────
    target_url  = models.URLField(max_length=512)

    # ── Schedule ──────────────────────────────────────────────────
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    finished_at  = models.DateTimeField(null=True, blank=True)

    # ── Status Machine ────────────────────────────────────────────
    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        SCHEDULED  = 'scheduled',  'Scheduled'
        DISPATCHED = 'dispatched', 'Dispatched'
        RUNNING    = 'running',    'Running'
        COMPLETED  = 'completed',  'Completed'
        FAILED     = 'failed',     'Failed'
        CANCELLED  = 'cancelled',  'Cancelled'

    status     = models.CharField(max_length=16, choices=Status.choices,
                                  default=Status.PENDING, db_index=True)
    worker     = models.ForeignKey('WorkerNode', null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='tasks')

    # ── Errors ────────────────────────────────────────────────────
    error_message = models.TextField(blank=True, default='')

    # ── Audit ──────────────────────────────────────────────────────
    created_by = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
```

**Fields Summary**

| Field | Type | Description |
|---|---|---|
| `id` | UUID PK | Task identifier |
| `name` | CharField(256) | Task name |
| `engine` | CharField (Enum) | k6 / jmeter / loadrunner |
| `script_path` | CharField(512) | Script path relative to engines/ |
| `parameters` | JSONField | Engine configuration parameters |
| `target_url` | URLField | Target URL base path |
| `scheduled_at` | DateTimeField | Execution schedule |
| `started_at` | DateTimeField | Actual task start time |
| `finished_at` | DateTimeField | Task completion time |
| `status` | CharField (Enum) | State machine status |
| `worker` | FK → WorkerNode | Assigned node |
| `error_message` | TextField | Error logs on failures |

---

### 2.3 `TestResult` — Test Result Details

Holds parsed summary metrics and raw reports.

```python
class TestResult(models.Model):

    # ── Identity ──────────────────────────────────────────────────
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField('LoadTestTask', on_delete=models.CASCADE,
                                related_name='result')

    # ── Reports ───────────────────────────────────────────────────
    raw_report = models.JSONField()

    # ── Summary Metrics ───────────────────────────────────────────
    total_requests      = models.PositiveIntegerField(default=0)
    failed_requests     = models.PositiveIntegerField(default=0)
    error_rate_pct      = models.FloatField(default=0.0)
    avg_response_ms     = models.FloatField(default=0.0)
    p90_response_ms     = models.FloatField(default=0.0)
    p95_response_ms     = models.FloatField(default=0.0)
    p99_response_ms     = models.FloatField(default=0.0)
    max_response_ms     = models.FloatField(default=0.0)
    throughput_rps      = models.FloatField(default=0.0)
    peak_vus            = models.PositiveIntegerField(default=0)

    # ── Threshold Assertion ───────────────────────────────────────
    thresholds_passed   = models.BooleanField(null=True, blank=True)
    thresholds_detail   = models.JSONField(default=list, blank=True)

    # ── Audit ──────────────────────────────────────────────────────
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-collected_at']
```

---

## 3. Dispatching and Result Collection Lifecycle

### 3.1 `LoadTestTask` State Machine

```
                      ┌─────────────────────────────────────────────┐
                      │                                             │
      Create Task     ▼           Celery Trigger                    │
  ──────────▶ [PENDING] ──────────────────────────▶ [SCHEDULED]  │
                  │                                      │         │
                  │ scheduled_at=null                    │ Time reached
                  │ (Run immediately)                    ▼         │
                  │                               Celery Trigger   │
                  └───────────────────────────▶ [DISPATCHED]      │
                                                      │            │
                                             Worker acknowledged   │ Any State
                                                      ▼            │ User Cancelled
                                                [RUNNING]          │
                                                  │     │           │
                                      Success     │     │ Timeout   │
                                                  ▼     ▼           │
                                           [COMPLETED] [FAILED] ───┘
                                                             ▲
                                                     [CANCELLED]
```

### 3.2 Sequence Diagram

```
User/API                  Control Plane              Celery              Worker Agent
    │                         │                        │                     │
    │── POST /api/tasks ──────▶│                        │                     │
    │   {engine, script,       │                        │                     │
    │    target_url, ...}      │                        │                     │
    │                         │── 1. Create LoadTestTask│                     │
    │                         │   status=PENDING        │                     │
    │                         │                         │                     │
    │                         │── 2. dispatch_task.     │                     │
    │                         │      delay(task_id) ───▶│                     │
    │                         │                         │                     │
    │◀── 202 Accepted ────────│                         │                     │
    │   {task_id, status}      │                        │                     │
    │                         │                        │                     │
    │                         │            3. Query online Worker            │
    │                         │◀────────── (WorkerNode.status=online) ───────│
    │                         │                        │                     │
    │                         │        4. status → DISPATCHED               │
    │                         │                        │                     │
    │                         │── 5. POST /execute ─────────────────────────▶│
    │                         │   {task_id, script,     │                    │
    │                         │    parameters, ...}     │                    │
    │                         │                        │                    │
    │                         │◀── 200 OK (accepted) ──────────────────────│
    │                         │                        │                    │
    │                         │        6. status → RUNNING                  │
    │                         │           started_at = now()                │
    │                         │                        │                    │
    │                         │                        │          7. Run Engine
    │                         │                        │   k6 run script.js  │
    │                         │                        │   --out json=...    │
    │                         │                        │                    │
    │                         │◀── 8. POST /results ───────────────────────│
    │                         │   {task_id, raw_report, │                   │
    │                         │    metrics_summary, ...}│                   │
    │                         │                        │                    │
    │                         │── 9. Save TestResult    │                    │
    │                         │   Parse raw_report      │                   │
    │                         │   Fill metrics          │                   │
    │                         │   status → COMPLETED     │                  │
    │                         │   finished_at = now()   │                   │
```

---

## 4. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/workers/` | List all registered worker nodes |
| `POST` | `/api/workers/` | Register a new worker node |
| `GET` | `/api/workers/{id}/` | Get details of a worker node |
| `POST` | `/api/workers/{id}/heartbeat/` | Heartbeat endpoint for worker node |
| `GET` | `/api/tasks/` | List all tasks |
| `POST` | `/api/tasks/` | Create a new load test task |
| `GET` | `/api/tasks/{id}/` | Get details of a task (includes results) |
| `DELETE` | `/api/tasks/{id}/` | Cancel a pending/scheduled task |
| `GET` | `/api/results/` | List all test results |
| `GET` | `/api/results/{id}/` | Get result details (includes raw_report) |
| `POST` | `/api/tasks/{id}/results/` | Submit task results from worker (Internal) |

---

## 5. Directory Structure

```
control-plane/
├── manage.py
├── requirements.txt            ← django, djangorestframework, celery, redis
├── config/                     ← Django settings project
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py      ← SQLite
│   │   └── production.py       ← PostgreSQL
│   ├── urls.py
│   └── celery.py               ← Celery configuration
├── apps/
│   ├── workers/                ← WorkerNode Model + API
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── tasks.py            ← Celery heartbeat checks
│   ├── tasks/                  ← LoadTestTask Model + API
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── tasks.py            ← Celery task dispatchers
│   └── results/                ← TestResult Model + API
│       ├── models.py
│       ├── serializers.py
│       ├── parsers.py          ← Report parsers
│       └── views.py
├── ARCHITECTURE.md             ← This file
└── Dockerfile
```

---

## 6. Architecture Decisions (ADR)

* **ADR-01: SQLite for MVP**: Zero-config, lightweight database for development. Production can seamlessly switch to PostgreSQL.
* **ADR-02: UUID Task IDs**: Prevents enumeration of tasks and provides random IDs for API submissions.
* **ADR-03: Storing Raw Report in JSON**: Retains full data granularity for retrospective analytics.
* **ADR-04: Indexed Summary Fields**: Fields like `p95_response_ms` are indexed directly in database columns for efficient sorting and listing.
* **ADR-05: Celery Beat for Health Sweeping**: Centralized cron loops mark nodes `OFFLINE` if no heartbeat is received within 30s.
