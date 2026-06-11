# 🐳 Docker Compose 本地驗證與除錯指南

> **pLoadtesting · 本地環境操作手冊**
> 適用版本：v0.1.0 · 環境需求：Docker Engine 24+、Docker Compose v2

---

## 服務概覽

| 服務名稱 | 容器名稱 | 對外 Port | 說明 |
|---|---|---|---|
| `target-app` | `ploadtesting-target-app` | `8000` | 壓測靶機（FastAPI） |
| `redis` | `ploadtesting-redis` | `6379` | Celery Broker |
| `control-plane-web` | `ploadtesting-control-plane-web` | `9000` | 中控 Web API（Django） |
| `control-plane-celery` | `ploadtesting-control-plane-celery` | — | Celery Worker + Beat |
| `worker-agent-1` | `ploadtesting-worker-agent-1` | — | 壓測執行節點（FastAPI :8100 內部） |
| `influxdb` | `ploadtesting-influxdb` | `8086` | 時序資料庫（Phase 6） |
| `grafana` | `ploadtesting-grafana` | `3000` | 即時監控儀表板（Phase 6） |

---

## 快速啟動

### Step 1：複製環境變數設定

```bash
# 建立本地 .env 檔（不會被 git 追蹤）
cat > .env << 'EOF'
# API 認證 Token（Control Plane ↔ Worker 通訊使用）
# 正式環境請替換為隨機強密鑰
PLOADTESTING_API_TOKEN=dev-api-token-change-me
EOF
```

### Step 2：建構並啟動所有服務

```bash
# 首次啟動（重新 Build 映像）
docker compose up --build -d

# 非首次啟動（直接啟動）
docker compose up -d
```

### Step 3：確認所有服務健康

```bash
docker compose ps
```

**預期輸出**（所有服務應為 `Up` 或 `Up (healthy)`）：

```
NAME                                  IMAGE                    STATUS
ploadtesting-target-app               ploadtesting-target-app  Up (healthy)
ploadtesting-redis                    redis:7-alpine           Up (healthy)
ploadtesting-control-plane-web        ploadtesting-control-...  Up
ploadtesting-control-plane-celery     ploadtesting-control-...  Up
ploadtesting-worker-agent-1           ploadtesting-worker-...  Up
ploadtesting-influxdb                 influxdb:2.7-alpine      Up (healthy)
ploadtesting-grafana                  grafana/grafana-oss:...  Up (healthy)
```

---

## 端點健康驗證

### 1. Target App

```bash
# 基本健康確認
curl -s http://localhost:8000/api/health
# 預期：{"status":"ok"}

# CPU 密集端點
curl -s "http://localhost:8000/api/cpu-bound?n=100000"
# 預期：{"status":"ok","result":...,"elapsed_ms":...}

# I/O 密集端點
curl -s "http://localhost:8000/api/io-bound?delay=0.5"
# 預期：{"status":"ok","delay":0.5}

# 資料序列化端點
curl -s -X POST http://localhost:8000/api/data \
  -H "Content-Type: application/json" \
  -d '{"id":1,"payload":"test"}' | python3 -m json.tool | head -5
# 預期：包含 100 筆 item 的 JSON 陣列

# Swagger UI
open http://localhost:8000/docs
```

### 2. Control Plane

```bash
# 設定 API Token（對應 .env 或 docker-compose 預設值）
export API_TOKEN="dev-api-token-change-me"

# 列出已註冊的 Worker 節點
curl -s http://localhost:9000/api/workers/ \
  -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" | python3 -m json.tool

# 列出所有任務
curl -s http://localhost:9000/api/tasks/ \
  -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" | python3 -m json.tool

# Django Admin（超級使用者帳號需先建立）
open http://localhost:9000/admin/
```

### 3. Worker Agent（透過 Control Plane 間接驗證）

```bash
# 等待約 10~15 秒後，Worker 應已完成首次心跳並出現在列表中
curl -s http://localhost:9000/api/workers/ \
  -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" | python3 -m json.tool
# 預期：worker-agent-1 status=online，last_heartbeat_at 為近期時間戳
```

### 4. InfluxDB（Phase 6）

```bash
# InfluxDB 健康確認
curl -s http://localhost:8086/health
# 預期：{"checks":[...],"message":"ready for queries and writes","status":"pass",...}

# InfluxDB UI（瀏覽器）
open http://localhost:8086
# 帳號：admin / ploadtesting-admin
```

### 5. Grafana（Phase 6）

```bash
# Grafana 健康確認
curl -s http://localhost:3000/api/health
# 預期：{"commit":"...","database":"ok","version":"..."}

# Grafana Dashboard（瀏覽器）
open http://localhost:3000
# 帳號：admin / admin
# 路徑：Dashboards → pLoadtesting — Load Test Monitor
```

---

## 端對端壓測驗證流程

完整驗證從任務建立到結果回傳的整個生命週期：

```bash
export API_TOKEN="dev-api-token-change-me"

# Step 1：建立 k6 Smoke Test 任務
TASK_RESPONSE=$(curl -s -X POST http://localhost:9000/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" \
  -d '{
    "name": "e2e-smoke-test",
    "engine": "k6",
    "script_path": "k6/smoke.js",
    "target_url": "http://target-app:8000"
  }')

echo "${TASK_RESPONSE}" | python3 -m json.tool
TASK_ID=$(echo "${TASK_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Task ID: ${TASK_ID}"

# Step 2：輪詢任務狀態（每 5 秒查詢一次）
for i in {1..10}; do
  STATUS=$(curl -s http://localhost:9000/api/tasks/${TASK_ID}/ \
    -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" | \
    python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))")
  echo "[$(date +%H:%M:%S)] Task status: ${STATUS}"
  [ "${STATUS}" = "completed" ] || [ "${STATUS}" = "failed" ] && break
  sleep 5
done

# Step 3：查看最終結果
curl -s http://localhost:9000/api/tasks/${TASK_ID}/ \
  -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" | python3 -m json.tool
```

---

## 常見服務管理指令

```bash
# 查看即時 Log（所有服務）
docker compose logs -f

# 查看特定服務 Log
docker compose logs -f control-plane-web
docker compose logs -f worker-agent-1
docker compose logs -f control-plane-celery

# 重啟特定服務
docker compose restart worker-agent-1

# 停止所有服務（保留 Volume）
docker compose stop

# 停止並移除容器（保留 Volume）
docker compose down

# 完全清理（移除容器 + Volume + 孤兒容器）
docker compose down -v --remove-orphans

# 重新 Build 特定服務
docker compose build control-plane-web
docker compose up -d control-plane-web
```

---

## 🔧 常見問題排除（FAQ）

### ❌ 問題 1：`control-plane-web` 啟動後立即 Exit

**症狀**：
```bash
docker compose ps
# control-plane-web   Exited (1)
```

**排查步驟**：
```bash
docker compose logs control-plane-web

# 若出現 "django.db.utils.OperationalError: no such table"
# 需先執行 migrate
docker compose exec control-plane-web python manage.py migrate

# 若出現 "ModuleNotFoundError"
# 需重新 Build 映像
docker compose build control-plane-web && docker compose up -d control-plane-web
```

---

### ❌ 問題 2：Worker Agent 未出現在 Control Plane Worker 列表

**症狀**：`/api/workers/` 回傳空陣列 `[]`

**排查步驟**：
```bash
# 1. 確認 Worker Agent 是否正在運行
docker compose ps worker-agent-1

# 2. 查看 Worker Agent 啟動 Log
docker compose logs worker-agent-1

# 3. 確認 CONTROL_PLANE_URL 環境變數正確
docker compose exec worker-agent-1 env | grep CONTROL_PLANE_URL
# 應為：CONTROL_PLANE_URL=http://control-plane-web:9000

# 4. 測試 Worker 容器內是否能連到 Control Plane
docker compose exec worker-agent-1 \
  python3 -c "import urllib.request; print(urllib.request.urlopen('http://control-plane-web:9000/api/workers/').status)"
# 應為：403（需 Token）或 200
```

---

### ❌ 問題 3：任務卡在 `PENDING` 狀態超過 1 分鐘

**症狀**：任務一直保持 `PENDING`，未被派發

**排查步驟**：
```bash
# 1. 確認 Celery Worker + Beat 是否運行
docker compose ps control-plane-celery
docker compose logs control-plane-celery | tail -20

# 2. 確認 Redis 連線正常
docker compose exec redis redis-cli ping
# 應回傳：PONG

# 3. 確認是否有 ONLINE 狀態的 Worker
curl -s http://localhost:9000/api/workers/ \
  -H "X-PLoadtesting-Api-Token: ${API_TOKEN}" | \
  python3 -c "import sys,json; [print(w['name'], w['status']) for w in json.load(sys.stdin)]"

# 4. 確認 Worker capabilities 包含任務所需的 engine
# 例如 k6 任務需要 Worker 具備 ["k6"] 能力
```

---

### ❌ 問題 4：API 回傳 403 Forbidden

**症狀**：
```json
{"detail": "Authentication credentials were not provided."}
```

**解決方式**：
```bash
# 在請求中加入 API Token Header
curl -H "X-PLoadtesting-Api-Token: dev-api-token-change-me" \
  http://localhost:9000/api/workers/

# 確認 .env 中的 Token 與 docker-compose 環境變數一致
grep PLOADTESTING_API_TOKEN .env
docker compose exec control-plane-web env | grep PLOADTESTING_API_TOKEN
```

---

### ❌ 問題 5：`docker compose up` 時 Port 衝突

**症狀**：
```
Error: bind: address already in use (port 8000 or 9000)
```

**解決方式**：
```bash
# 找出占用 Port 的程序
lsof -i :8000
lsof -i :9000

# 終止程序（替換 <PID>）
kill -9 <PID>

# 或修改 docker-compose.yml 中的 ports 對應（左側為 Host Port）
# e.g. "18000:8000" 改用 18000 對外
```

---

## 資源監控

```bash
# 即時查看所有容器資源使用量
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 預期基準值（閒置狀態）
# target-app:              < 1% CPU, ~50-80MB RAM
# redis:                   < 1% CPU, ~10MB RAM
# control-plane-web:       < 1% CPU, ~120-180MB RAM
# control-plane-celery:    < 1% CPU, ~120-180MB RAM
# worker-agent-1:          < 1% CPU, ~50-80MB RAM
# influxdb:                < 1% CPU, ~80-150MB RAM
# grafana:                 < 1% CPU, ~80-120MB RAM
```

---

## ❌ 問題 6：InfluxDB 初始化失敗 / Token 變更後無法啟動

**症狀**：`influxdb` 容器持續 Restart，或 Grafana 顯示「datasource connection error」

**原因**：更改了 `INFLUXDB_TOKEN` 環境變數，但 Volume 中已有舊的 token 資料。

**解決方式**：
```bash
# 停止並移除 InfluxDB Volume（會清除所有歷史數據）
docker compose down
docker volume rm ploadtesting_influxdb-data
docker compose up -d

# 重新啟動後，InfluxDB 會以新 token 重新初始化
```

> **注意**：移除 Volume 會清除所有已寫入的壓測指標。正式環境請先備份再操作。

---

## 相關文件

- [Observability Guide](./observability-guide.md) — InfluxDB + Grafana 詳細說明
- [k6 Smoke Test Guide](./k6-smoke-test-guide.md)
- [Architecture Interaction](./architecture-interaction.md)
