# 🏗️ 架構互動圖 — Control Plane 與 Worker Agent

> **pLoadtesting · 系統互動文件**
> 版本：1.0.0 · 對應版本：v0.1.0

本文件以 Mermaid 圖表描述 Control Plane 與 Worker Agent 之間的三大核心互動機制。

---

## 1. 心跳機制（Heartbeat）

Worker Agent 每 10 秒向 Control Plane 發送一次心跳，附帶當前 CPU/記憶體使用率。
Control Plane 的 Celery Beat 每 30 秒執行一次 `mark_stale_workers` 任務，將超時節點標記為 `offline`。

```mermaid
sequenceDiagram
    participant W as Worker Agent<br/>(FastAPI :8100)
    participant CP as Control Plane<br/>(Django :9000)
    participant CB as Celery Beat<br/>(排程器)
    participant DB as SQLite DB<br/>(WorkerNode)

    Note over W: 啟動時自動註冊

    W->>CP: POST /api/workers/<br/>{ name, ip, port, capabilities }
    CP->>DB: 建立 WorkerNode<br/>status=online
    CP-->>W: 201 Created { worker_id }

    loop 每 10 秒
        W->>W: psutil 採集<br/>cpu_pct, mem_pct
        W->>CP: POST /api/workers/{id}/heartbeat/<br/>{ cpu_pct, mem_pct, active_task_count }
        CP->>DB: 更新 last_heartbeat_at<br/>resource_snapshot
        CP-->>W: 200 OK
    end

    loop 每 30 秒（Celery Beat）
        CB->>CP: 觸發 mark_stale_workers
        CP->>DB: 查詢 last_heartbeat_at < now()-30s
        DB-->>CP: 逾時節點清單
        CP->>DB: 批次更新 status=offline
    end
```

---

## 2. 任務派發循環（Task Dispatch）

`dispatch_pending_tasks` 由 Celery Beat 定期觸發，自動將 `PENDING` 任務派發至空閒且具備對應能力的 Worker。

```mermaid
sequenceDiagram
    participant U as 使用者 / API Client
    participant CP as Control Plane<br/>(Django :9000)
    participant CB as Celery Beat
    participant DB as SQLite DB
    participant W as Worker Agent<br/>(FastAPI :8100)

    U->>CP: POST /api/tasks/<br/>{ engine, script_path, target_url, ... }
    CP->>DB: 建立 LoadTestTask<br/>status=PENDING
    CP-->>U: 202 Accepted { task_id }

    loop Celery Beat 週期觸發
        CB->>CP: dispatch_pending_tasks()
        CP->>DB: 查詢 PENDING 任務
        DB-->>CP: [task_1, task_2, ...]

        loop 每個 PENDING 任務
            CP->>DB: 查詢 status=online<br/>且 capabilities 包含 engine<br/>且 active_task_count=0
            DB-->>CP: idle_worker（或無可用節點）

            alt 找到可用 Worker
                CP->>DB: task.status → DISPATCHED<br/>task.worker = idle_worker
                CP->>W: POST /execute<br/>{ task_id, script_path, target_url, parameters }
                W-->>CP: 202 Accepted
                CP->>DB: task.status → RUNNING<br/>started_at = now()
                CP->>DB: worker.active_task_count += 1
            else 無可用 Worker
                CP->>DB: task.error_message 記錄原因
                Note over CP: 保留 PENDING，下次週期重試
            end
        end
    end
```

---

## 3. 任務執行與結果回傳（Execution & Result Collection）

Worker Agent 在背景執行引擎腳本，完成後解析輸出指標並回傳 Control Plane。

```mermaid
sequenceDiagram
    participant CP as Control Plane<br/>(Django :9000)
    participant W as Worker Agent<br/>(FastAPI :8100)
    participant E as 引擎子程序<br/>(k6 / JMeter)
    participant T as Target App<br/>(FastAPI :8000)

    CP->>W: POST /execute<br/>{ task_id, engine, script_path,<br/>  target_url, parameters }
    W->>W: 背景 asyncio.create_task()
    W-->>CP: 202 Accepted

    Note over W,E: 非同步背景執行

    W->>E: subprocess 啟動<br/>k6 run script.js --out json=...<br/>或 jmeter -n -t plan.jmx -l results.jtl
    E->>T: HTTP 請求壓測<br/>GET /api/health, /api/cpu-bound 等

    alt k6 執行
        E-->>W: 輸出 JSON（metrics, checks, thresholds）
        W->>W: 解析 k6 JSON<br/>提取 rps, p95, error_rate
    else JMeter 執行
        E-->>W: 輸出 results.jtl（CSV 格式）
        W->>W: csv.DictReader 解析<br/>提取 rps, p95, error_rate
    end

    alt 執行成功
        W->>CP: POST /api/tasks/{id}/results/<br/>{ execution_status: "success",<br/>  raw_report: {...},<br/>  metrics_summary: { rps, p95, ... } }
        CP->>CP: 建立 TestResult<br/>status → COMPLETED<br/>finished_at = now()
    else 執行失敗
        W->>CP: POST /api/tasks/{id}/results/<br/>{ execution_status: "failed",<br/>  error_message: "exit code 107" }
        CP->>CP: 建立 TestResult<br/>status → FAILED
    end

    CP->>CP: worker.active_task_count -= 1
    CP->>CP: worker.status → online（若無其他任務）
```

---

## 4. LoadTestTask 狀態機

```mermaid
stateDiagram-v2
    [*] --> PENDING : POST /api/tasks/ 建立任務

    PENDING --> DISPATCHED : Celery Beat 找到可用 Worker<br/>POST /execute 成功
    PENDING --> PENDING : 無可用 Worker（下次週期重試）

    DISPATCHED --> RUNNING : Worker 確認收到任務<br/>started_at = now()

    RUNNING --> COMPLETED : Worker 回傳 execution_status=success<br/>finished_at = now()
    RUNNING --> FAILED : Worker 回傳 execution_status=failed<br/>或執行逾時

    PENDING --> CANCELLED : 使用者 DELETE /api/tasks/{id}/
    DISPATCHED --> CANCELLED : 使用者取消
    RUNNING --> CANCELLED : 使用者強制取消

    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]
```

---

## 5. 系統拓撲概覽

```mermaid
graph TB
    subgraph nebula_network["🌐 ploadtesting-net (Docker Bridge)"]
        subgraph CP["🖥️ Control Plane"]
            CPW["control-plane-web<br/>Django :9000"]
            CPC["control-plane-celery<br/>Celery Worker + Beat"]
        end

        REDIS["🔴 Redis :6379<br/>Celery Broker"]
        DB["💾 SQLite<br/>WorkerNode / LoadTestTask / TestResult"]

        subgraph WA["🤖 Worker Agent"]
            W1["worker-agent-1<br/>FastAPI :8100"]
        end

        TARGET["🎯 Target App<br/>FastAPI :8000"]
    end

    CPW <-->|Django ORM| DB
    CPW <-->|REST API| WA
    CPC <-->|Celery Tasks| REDIS
    CPW <-->|Celery App| REDIS
    W1 -->|10s Heartbeat| CPW
    W1 -->|回傳測試結果| CPW
    W1 -->|HTTP 壓測| TARGET
```
