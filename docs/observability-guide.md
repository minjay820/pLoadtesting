# Observability Guide — InfluxDB v2 + Grafana

> Phase 6 可觀測性整合說明。提供壓測期間即時數據串流至 InfluxDB，並透過 Grafana 視覺化呈現。

---

## 架構概覽

```
k6 (--out influxdb)   ──┐
                         ├──→ InfluxDB v2 :8086 ──→ Grafana :3000
JMeter (Backend Listener)─┘         ↑
Worker Agent (summary push) ─────────┘
```

### 兩條數據路徑

| 路徑 | 說明 | 延遲 |
|---|---|---|
| **即時串流** | k6/JMeter 每秒直接寫入 InfluxDB | ~1 秒 |
| **彙總寫入** | 壓測完成後 Worker push 摘要指標 | 任務結束時 |

即時串流提供 Dashboard 即時曲線，彙總寫入確保 `task_summary` measurement 完整保存。

---

## 快速啟動

### 啟動完整 Stack

```bash
docker compose up -d
```

所有 7 個服務將啟動，包含 InfluxDB 與 Grafana。

### 確認服務健康

```bash
# InfluxDB 健康檢查
curl http://localhost:8086/health

# Grafana 健康檢查
curl http://localhost:3000/api/health
```

### 開啟 Grafana Dashboard

1. 瀏覽器開啟 [http://localhost:3000](http://localhost:3000)
2. 帳號密碼：`admin` / `admin`
3. 左側選單 → Dashboards → 選擇 **pLoadtesting — Load Test Monitor**

### 開啟 InfluxDB UI

1. 瀏覽器開啟 [http://localhost:8086](http://localhost:8086)
2. 帳號密碼：`admin` / `ploadtesting-admin`（或環境變數 `INFLUXDB_ADMIN_PASSWORD`）
3. Organization：`ploadtesting`，Bucket：`load_tests`

---

## 環境變數設定

在 `.env` 檔案（或 `docker-compose.yml` 環境變數）中設定：

```dotenv
# InfluxDB 初始設定
INFLUXDB_TOKEN=ploadtesting-dev-token
INFLUXDB_ORG=ploadtesting
INFLUXDB_BUCKET=load_tests
INFLUXDB_ADMIN_PASSWORD=ploadtesting-admin

# Grafana
GRAFANA_ADMIN_PASSWORD=admin
```

> **Production 注意**：請務必替換為強密碼，並關閉 Grafana 匿名存取（`GF_AUTH_ANONYMOUS_ENABLED=false`）。

---

## Grafana Dashboard 面板說明

| 面板 | 說明 | 資料來源 |
|---|---|---|
| **即時 RPS** | 每秒請求數曲線（每秒更新） | k6 `http_reqs` measurement |
| **P95 回應時間** | 95th percentile 延遲趨勢（ms） | k6 `http_req_duration` |
| **P99 回應時間** | 99th percentile 延遲趨勢（ms） | k6 `http_req_duration` |
| **HTTP 錯誤率** | 4xx/5xx 錯誤百分比（紅色警示區域） | k6 `http_req_failed` |
| **Virtual Users** | 並發 VU 數量曲線 | k6 `vus` measurement |
| **任務彙總** | Task ID、Engine、avg/p95、RPS | Worker `task_summary` measurement |

---

## k6 InfluxDB 輸出說明

Worker Agent 會自動偵測 `INFLUXDB_URL` 環境變數，若已設定，則在執行 k6 時自動加入 `--out influxdb` 參數：

```bash
# Worker 實際執行的指令（自動組成）
k6 run \
  --out json=/tmp/result_<task_id>.json \
  --out "influxdb=http://influxdb:8086?org=ploadtesting&bucket=load_tests&token=<token>" \
  engines/k6/smoke.js
```

k6 v0.51 使用 InfluxDB v1 line protocol 寫入，InfluxDB v2 透過內建 v1 compatibility API 接收，**不需要安裝任何 extension**。

---

## 自訂 Dashboard

### 修改現有 Dashboard

Dashboard 以 JSON Provisioning 方式自動載入，位於：

```
observability/grafana/provisioning/dashboards/ploadtesting.json
```

修改後，重啟 Grafana 即自動載入：

```bash
docker compose restart grafana
```

### 在 Grafana UI 手動建立 Panel

1. 進入 Dashboard → 右上角 **Edit** → **Add Panel**
2. 選擇 `InfluxDB-pLoadtesting` 作為 Data Source
3. 使用 **Flux** 查詢語言，例如：

```flux
from(bucket: "load_tests")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "http_req_duration")
  |> filter(fn: (r) => r._field == "value")
  |> aggregateWindow(every: v.windowPeriod, fn: mean)
```

### 匯出 Dashboard JSON

在 Grafana UI → Dashboard Settings → JSON Model → 複製 JSON 取代 `ploadtesting.json`。

---

## Measurements 結構

### k6 原生 Measurements

k6 透過 `--out influxdb` 自動寫入以下 measurements：

| Measurement | 說明 |
|---|---|
| `http_reqs` | 請求計數 |
| `http_req_duration` | 回應時間（ms） |
| `http_req_failed` | 失敗請求比例 |
| `vus` | 當前 Virtual User 數量 |
| `vus_max` | 最大 VU 數量 |
| `iterations` | 完成的迭代次數 |

### Worker 彙總 Measurement

壓測完成後 Worker 寫入：

```
Measurement: task_summary
Tags:   task_id, engine, worker, status, target_url
Fields: avg_response_ms, p95_response_ms, throughput_rps,
        error_rate_pct, total_requests, failed_requests
```

---

## 故障排除

### Grafana 顯示「No data」

1. 確認 InfluxDB 健康：`curl http://localhost:8086/health`
2. 確認 Datasource 連線：Grafana → Connections → Data Sources → Test
3. 確認壓測已執行且有寫入：InfluxDB UI → Data Explorer → bucket `load_tests`
4. 調整 Dashboard 時間範圍（右上角）至包含壓測期間

### k6 InfluxDB 串流失敗

檢查 Worker 日誌：

```bash
docker logs ploadtesting-worker-agent-1 --tail=50
```

尋找 `[InfluxDB]` 開頭的日誌行。若串流失敗，Worker 仍會在任務完成後執行彙總 push。

### InfluxDB 初始化失敗

若更改了 `INFLUXDB_TOKEN` 但 Volume 已存在：

```bash
docker compose down
docker volume rm ploadtesting_influxdb-data
docker compose up -d
```

---

## 相關文件

- [本機驗證指南](./local-validation-guide.md)
- [k6 Smoke Test 指南](./k6-smoke-test-guide.md)
- [架構互動說明](./architecture-interaction.md)
