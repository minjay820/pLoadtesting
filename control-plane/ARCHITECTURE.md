# 🖥️ Control Plane — 架構設計文件

> **pLoadtesting · Control Plane MVP**
> 技術棧：Python Django + Django REST Framework · SQLite (MVP) · Celery + Redis
> 文件版本：1.0.0 · Phase 4 架構藍圖

---

## 一、系統定位

Control Plane 是 pLoadtesting 生態系統的「神經中樞」，負責：

1. **任務管理**：接收使用者建立的壓測任務，選擇引擎腳本與目標 URL
2. **Worker 調度**：將任務派發至可用的 Worker 節點執行
3. **結果彙整**：收集 Worker 回傳的 k6/JMeter JSON 報表，解析並持久化
4. **Web UI**：提供 RESTful API 供前端 Dashboard 查詢與操作

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
                   │  (遠端節點)        │   │  k6 CLI    │
                   └───────────────────┘   └────────────┘
```

---

## 二、資料庫結構設計 (Django Models 藍圖)

### 2.1 `WorkerNode` — 遠端節點登記表

記錄所有曾向 Control Plane 註冊的 Worker 節點，Control Plane 依此表選擇可用節點。

```python
class WorkerNode(models.Model):

    # ── 識別 ──────────────────────────────────────────────────
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Worker 自報的唯一名稱（e.g. "worker-taipei-01"）
    name       = models.CharField(max_length=128, unique=True)
    # Worker 的可達位址（Control Plane 用來推送任務）
    ip_address = models.GenericIPAddressField()
    port       = models.PositiveIntegerField(default=8100)

    # ── 狀態 ──────────────────────────────────────────────────
    class Status(models.TextChoices):
        ONLINE   = 'online',   '在線可用'
        BUSY     = 'busy',     '執行中'
        OFFLINE  = 'offline',  '離線'
        DRAINING = 'draining', '排水中（不接新任務）'

    status        = models.CharField(max_length=16, choices=Status.choices,
                                     default=Status.OFFLINE, db_index=True)
    # Worker 支援的引擎列表（JSON Array，e.g. ["k6", "jmeter"]）
    capabilities  = models.JSONField(default=list)

    # ── 可觀測性 ───────────────────────────────────────────────
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    # Worker 自報的資源使用率快照（CPU %、Memory %）
    resource_snapshot = models.JSONField(default=dict, blank=True)
    # 該 Worker 目前正在執行的任務數
    active_task_count = models.PositiveIntegerField(default=0)

    # ── 稽核 ──────────────────────────────────────────────────
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_heartbeat_at']

    def is_alive(self, timeout_seconds: int = 30) -> bool:
        """判斷節點是否在 timeout 內有心跳，用於自動標記 OFFLINE。"""
        if not self.last_heartbeat_at:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.last_heartbeat_at >= timezone.now() - timedelta(seconds=timeout_seconds)
```

**欄位速查表**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | UUID PK | 不可猜測的唯一識別碼 |
| `name` | CharField(128) | Worker 自報名稱，全域唯一 |
| `ip_address` | GenericIPAddressField | 支援 IPv4 / IPv6 |
| `port` | PositiveIntegerField | Worker Agent 監聽 Port，預設 8100 |
| `status` | CharField (Enum) | online / busy / offline / draining |
| `capabilities` | JSONField | `["k6", "jmeter"]` 等引擎清單 |
| `last_heartbeat_at` | DateTimeField | Worker 最後一次心跳的 UTC 時間 |
| `resource_snapshot` | JSONField | `{"cpu_pct": 23.5, "mem_pct": 41.2}` |
| `active_task_count` | PositiveIntegerField | 目前正在執行的任務數量 |
| `registered_at` | DateTimeField | 首次註冊時間（自動填入） |
| `updated_at` | DateTimeField | 最後更新時間（自動維護） |

---

### 2.2 `LoadTestTask` — 壓測任務主表

每筆記錄代表一次使用者發起的壓測任務，從建立到完成的完整生命週期都在此記錄。

```python
class LoadTestTask(models.Model):

    # ── 識別 ──────────────────────────────────────────────────
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=256,
                                   help_text="任務友善名稱，e.g. 'Sprint-42 壓測'")

    # ── 引擎與腳本設定 ─────────────────────────────────────────
    class Engine(models.TextChoices):
        K6         = 'k6',         'k6'
        JMETER     = 'jmeter',     'JMeter'
        LOADRUNNER = 'loadrunner', 'LoadRunner'

    engine      = models.CharField(max_length=16, choices=Engine.choices, db_index=True)
    # 相對於 engines/ 目錄的腳本路徑，e.g. "k6/stress_cpu.js"
    script_path = models.CharField(max_length=512)
    # 傳遞給引擎的額外參數（e.g. {"TARGET_URL": "http://...", "VUS": 50}）
    parameters  = models.JSONField(default=dict, blank=True)

    # ── 打擊目標 ───────────────────────────────────────────────
    target_url  = models.URLField(max_length=512,
                                  help_text="靶機 Base URL，e.g. http://localhost:8000")

    # ── 排程 ──────────────────────────────────────────────────
    scheduled_at = models.DateTimeField(null=True, blank=True,
                                        help_text="預計執行時間；null = 立即執行")
    started_at   = models.DateTimeField(null=True, blank=True)
    finished_at  = models.DateTimeField(null=True, blank=True)

    # ── 狀態機 ────────────────────────────────────────────────
    class Status(models.TextChoices):
        PENDING    = 'pending',    '待派發'
        SCHEDULED  = 'scheduled',  '已排程'
        DISPATCHED = 'dispatched', '已派發至 Worker'
        RUNNING    = 'running',    '執行中'
        COMPLETED  = 'completed',  '已完成'
        FAILED     = 'failed',     '失敗'
        CANCELLED  = 'cancelled',  '已取消'

    status     = models.CharField(max_length=16, choices=Status.choices,
                                  default=Status.PENDING, db_index=True)
    # 執行此任務的 Worker（任務完成後不刪除 FK，保留歷史）
    worker     = models.ForeignKey('WorkerNode', null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='tasks')

    # ── 失敗資訊 ───────────────────────────────────────────────
    # 失敗原因摘要（e.g. "Worker timeout", "Script not found"）
    error_message = models.TextField(blank=True, default='')

    # ── 稽核 ──────────────────────────────────────────────────
    created_by = models.CharField(max_length=128, blank=True,
                                  help_text="建立者識別（Phase 4 MVP 先用字串，後續整合 Auth）")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def duration_seconds(self) -> float | None:
        """計算任務實際執行秒數（finished_at - started_at）。"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
```

**欄位速查表**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | UUID PK | 任務唯一識別碼 |
| `name` | CharField(256) | 使用者友善名稱 |
| `engine` | CharField (Enum) | k6 / jmeter / loadrunner |
| `script_path` | CharField(512) | 相對腳本路徑，e.g. `k6/smoke.js` |
| `parameters` | JSONField | 動態引擎參數字典 |
| `target_url` | URLField | 靶機完整 URL |
| `scheduled_at` | DateTimeField (nullable) | 預計執行時間；`null` = 立即 |
| `started_at` | DateTimeField (nullable) | Celery worker 實際開始時間 |
| `finished_at` | DateTimeField (nullable) | 任務結束時間 |
| `status` | CharField (Enum) | 7 態狀態機（見下方生命週期） |
| `worker` | FK → WorkerNode | 執行節點；完成後保留歷史 |
| `error_message` | TextField | 失敗原因；成功時為空字串 |
| `created_by` | CharField(128) | 建立者（MVP 先用字串） |

---

### 2.3 `TestResult` — 壓測結果明細表

每個 `LoadTestTask` 對應**一筆** `TestResult`，儲存引擎回傳的完整報表與解析後的摘要指標。

```python
class TestResult(models.Model):

    # ── 識別（One-to-One 對應一個任務） ───────────────────────
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField('LoadTestTask', on_delete=models.CASCADE,
                                related_name='result')

    # ── 原始報表 ────────────────────────────────────────────────
    # k6 --out json 的原始 JSON Lines 字串，或 JMeter JTL 轉換後的 JSON
    # 大型報表建議後續遷移至 FileField 或物件儲存（S3/GCS）
    raw_report = models.JSONField(
        help_text="引擎原始輸出（k6 JSON Lines 解析後的結構化物件）"
    )

    # ── 解析後的摘要指標（供 Dashboard 快速查詢，無需重新解析 raw_report） ──
    total_requests      = models.PositiveIntegerField(default=0)
    failed_requests     = models.PositiveIntegerField(default=0)
    error_rate_pct      = models.FloatField(default=0.0,
                                            help_text="失敗率百分比，e.g. 2.5 表示 2.5%")
    avg_response_ms     = models.FloatField(default=0.0)
    p90_response_ms     = models.FloatField(default=0.0)
    p95_response_ms     = models.FloatField(default=0.0)
    p99_response_ms     = models.FloatField(default=0.0)
    max_response_ms     = models.FloatField(default=0.0)
    throughput_rps      = models.FloatField(default=0.0,
                                            help_text="每秒請求數 (requests/second)")
    peak_vus            = models.PositiveIntegerField(default=0,
                                                      help_text="壓測期間最大虛擬使用者數")

    # ── Threshold 判定結果 ─────────────────────────────────────
    # k6 Thresholds 或 JMeter Assertions 的整體通過/失敗
    thresholds_passed   = models.BooleanField(null=True, blank=True,
                                              help_text="null = 未設定 Thresholds")
    # 各 Threshold 詳細結果（e.g. [{"metric": "p(95)<2000", "passed": false}]）
    thresholds_detail   = models.JSONField(default=list, blank=True)

    # ── 稽核 ──────────────────────────────────────────────────
    collected_at = models.DateTimeField(auto_now_add=True,
                                        help_text="Control Plane 收到結果的時間")

    class Meta:
        ordering = ['-collected_at']
```

**欄位速查表**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | UUID PK | 結果唯一識別碼 |
| `task` | OneToOneField | 關聯的壓測任務 |
| `raw_report` | JSONField | 引擎完整原始輸出 |
| `total_requests` | PositiveIntegerField | 總請求數 |
| `failed_requests` | PositiveIntegerField | 失敗請求數 |
| `error_rate_pct` | FloatField | 失敗率 %（e.g. `2.5`） |
| `avg_response_ms` | FloatField | 平均回應時間 ms |
| `p90_response_ms` | FloatField | P90 回應時間 ms |
| `p95_response_ms` | FloatField | P95 回應時間 ms |
| `p99_response_ms` | FloatField | P99 回應時間 ms |
| `max_response_ms` | FloatField | 最大回應時間 ms |
| `throughput_rps` | FloatField | 每秒請求數 |
| `peak_vus` | PositiveIntegerField | 峰值虛擬使用者數 |
| `thresholds_passed` | BooleanField (nullable) | 整體 Threshold 是否通過 |
| `thresholds_detail` | JSONField | 各 Threshold 詳細結果陣列 |
| `collected_at` | DateTimeField | Control Plane 收到結果時間 |

---

### 2.4 ER 圖

```
┌──────────────────┐         ┌───────────────────────────┐
│   WorkerNode     │         │      LoadTestTask          │
│──────────────────│         │───────────────────────────│
│ id (UUID PK)     │         │ id (UUID PK)               │
│ name             │◀─────── │ worker (FK, nullable)      │
│ ip_address       │  0..*   │ name                       │
│ port             │         │ engine                     │
│ status           │         │ script_path                │
│ capabilities     │         │ parameters (JSON)          │
│ last_heartbeat   │         │ target_url                 │
│ resource_snapshot│         │ scheduled_at               │
│ active_task_count│         │ started_at                 │
│ registered_at    │         │ finished_at                │
│ updated_at       │         │ status                     │
└──────────────────┘         │ error_message              │
                             │ created_by                 │
                             │ created_at / updated_at    │
                             └───────────┬───────────────┘
                                         │ 1
                                         │
                                         │ 1
                             ┌───────────▼───────────────┐
                             │       TestResult           │
                             │───────────────────────────│
                             │ id (UUID PK)               │
                             │ task (OneToOne FK)         │
                             │ raw_report (JSON)          │
                             │ total_requests             │
                             │ failed_requests            │
                             │ error_rate_pct             │
                             │ avg / p90 / p95 / p99 /   │
                             │   max response_ms          │
                             │ throughput_rps             │
                             │ peak_vus                   │
                             │ thresholds_passed          │
                             │ thresholds_detail (JSON)   │
                             │ collected_at               │
                             └───────────────────────────┘
```

---

## 三、任務派發與收集的生命週期

### 3.1 `LoadTestTask` 狀態機

```
                     ┌─────────────────────────────────────────────┐
                     │                                             │
    建立任務           ▼          Celery 排程觸發                    │
  ──────────▶ [PENDING] ──────────────────────────▶ [SCHEDULED]  │
                  │                                      │         │
                  │ scheduled_at=null                    │ 到達時間  │
                  │ (立即執行)                            ▼         │
                  │                               Celery 觸發      │
                  └───────────────────────────▶ [DISPATCHED]      │
                                                      │            │
                                            Worker 確認接收         │ 任意階段
                                                      ▼            │ 使用者取消
                                               [RUNNING]          │
                                                 │     │           │
                                     成功完成      │     │ 異常/逾時  │
                                                 ▼     ▼           │
                                          [COMPLETED] [FAILED] ───┘
                                                            ▲
                                                    [CANCELLED]
```

### 3.2 完整生命週期：從建立到結果收集

```
使用者/API                Control Plane              Celery              Worker Agent
    │                         │                        │                     │
    │── POST /api/tasks ──────▶│                        │                     │
    │   {engine, script,       │                        │                     │
    │    target_url, ...}      │                        │                     │
    │                         │── 1. 建立 LoadTestTask ─│                     │
    │                         │   status=PENDING        │                     │
    │                         │                         │                     │
    │                         │── 2. dispatch_task.     │                     │
    │                         │      delay(task_id) ───▶│                     │
    │                         │                         │                     │
    │◀── 202 Accepted ────────│                         │                     │
    │   {task_id, status}      │                        │                     │
    │                         │                        │                     │
    │                         │            3. 查詢可用 Worker              │
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
    │                         │                        │          7. 執行引擎│
    │                         │                        │   k6 run script.js  │
    │                         │                        │   --out json=...    │
    │                         │                        │                    │
    │                         │◀── 8. POST /results ───────────────────────│
    │                         │   {task_id, raw_report, │                   │
    │                         │    metrics_summary, ...}│                   │
    │                         │                        │                    │
    │                         │── 9. 建立 TestResult    │                    │
    │                         │   解析 raw_report        │                   │
    │                         │   填入摘要指標            │                   │
    │                         │   status → COMPLETED     │                  │
    │                         │   finished_at = now()   │                   │
    │                         │                        │                    │
    │── GET /api/tasks/{id} ──▶│                        │                    │
    │◀── 200 {result: {...}} ─│                        │                    │
```

### 3.3 Celery 任務清單

| Celery Task | 觸發時機 | 說明 |
|---|---|---|
| `dispatch_task(task_id)` | 任務建立時，或 `scheduled_at` 到達時 | 選擇可用 Worker，發送執行指令 |
| `collect_heartbeats()` | Celery Beat，每 15 秒 | 輪詢所有 Worker 的心跳，更新 `status` |
| `mark_stale_workers()` | Celery Beat，每 60 秒 | 超過 30 秒無心跳的節點標記為 `OFFLINE` |
| `timeout_running_tasks()` | Celery Beat，每 60 秒 | 超過 `max_duration` 未完成的任務標記 `FAILED` |
| `retry_failed_dispatch(task_id)` | `dispatch_task` 失敗時 | 指數退避重試，最多 3 次 |

### 3.4 Worker 心跳機制

Worker Agent 每 **10 秒**向 Control Plane 發送一次心跳：

```
POST /api/workers/{worker_id}/heartbeat
{
  "status":            "online" | "busy",
  "active_task_count": 2,
  "resource_snapshot": {
    "cpu_pct":  45.3,
    "mem_pct":  62.1,
    "disk_pct": 18.5
  }
}
```

Control Plane 更新 `WorkerNode.last_heartbeat_at` 與 `resource_snapshot`。
Celery Beat 每 60 秒執行 `mark_stale_workers()`，將超過 30 秒無心跳的節點標記為 `OFFLINE`。

---

## 四、DRF API Endpoints 規劃

| Method | Path | 說明 |
|---|---|---|
| `GET` | `/api/workers/` | 列出所有 Worker 節點 |
| `POST` | `/api/workers/` | 新增 Worker 節點（Worker 自我註冊） |
| `GET` | `/api/workers/{id}/` | 查詢單一 Worker 詳情 |
| `POST` | `/api/workers/{id}/heartbeat/` | Worker 心跳回報 |
| `GET` | `/api/tasks/` | 列出所有任務（支援 status 過濾） |
| `POST` | `/api/tasks/` | 建立新壓測任務 |
| `GET` | `/api/tasks/{id}/` | 查詢任務詳情（含結果） |
| `DELETE` | `/api/tasks/{id}/` | 取消待執行任務（status → CANCELLED） |
| `GET` | `/api/results/` | 列出所有測試結果 |
| `GET` | `/api/results/{id}/` | 查詢單一結果詳情（含 raw_report） |
| `POST` | `/api/tasks/{id}/results/` | Worker 回傳測試結果（內部介面） |

---

## 五、目錄結構規劃（Django Project）

```
control-plane/
├── manage.py
├── requirements.txt            ← django, djangorestframework, celery, redis
├── config/                     ← Django project 設定
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py      ← SQLite
│   │   └── production.py      ← PostgreSQL（未來）
│   ├── urls.py
│   └── celery.py               ← Celery app 初始化
├── apps/
│   ├── workers/                ← WorkerNode Model + API
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── tasks.py            ← Celery 心跳任務
│   ├── tasks/                  ← LoadTestTask Model + API
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── tasks.py            ← Celery 派發任務
│   └── results/                ← TestResult Model + API
│       ├── models.py
│       ├── serializers.py
│       ├── parsers.py          ← k6/JMeter 原始報表解析器
│       └── views.py
├── ARCHITECTURE.md             ← 本文件
└── Dockerfile
```

---

## 六、技術決策紀錄 (ADR)

| # | 決策 | 原因 |
|:---:|---|---|
| ADR-01 | MVP 使用 SQLite | 零設定、易於開發與測試；後續可無縫遷移至 PostgreSQL |
| ADR-02 | 任務 ID 使用 UUID | 防止任務 ID 被枚舉；Worker 回傳結果時以 UUID 對應 |
| ADR-03 | `raw_report` 儲存完整 JSON | 保留原始數據，供未來重新解析或新增指標時使用 |
| ADR-04 | 摘要指標欄位化 | `p95_response_ms` 等欄位允許 Django ORM 直接過濾/排序，無需解析 JSON |
| ADR-05 | Celery Beat 做健康巡邏 | 集中式心跳超時判斷，避免 Worker 自報下線的可靠性問題 |
| ADR-06 | Worker 自我註冊 | Control Plane 無需預先設定節點 IP，支援動態擴縮容 |
