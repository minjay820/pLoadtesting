# 📊 k6 Smoke Test 使用指南與預期輸出

> **pLoadtesting · k6 使用文件**
> 適用版本：v0.1.0 · 腳本位置：`engines/k6/smoke.js`

---

## 概述

Smoke Test 是壓測流程的第一道關卡，目的是以**最低負載（1 VU × 10 秒）**確認靶機服務存活、端點響應正常。  
在任何 Stress / Load Test 前，**務必先跑 Smoke Test** 確保環境健康。

| 參數 | 值 |
|---|---|
| 測試端點 | `GET /api/health` |
| 虛擬使用者（VU） | 1 |
| 持續時間 | 10 秒 |
| 預期 HTTP 成功率 | 100% |
| p99 響應時間門檻 | < 500ms |

---

## 前置條件

### 本地直接執行（需安裝 k6）

```bash
# macOS
brew install k6

# Linux（Debian/Ubuntu）
sudo gpg -k
sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# 驗證安裝
k6 version
```

### Docker 環境（透過 Worker Agent 執行）

確認所有服務已啟動並健康：

```bash
docker compose up -d
docker compose ps
# 確認所有服務 Status 為 Up 或 healthy
```

---

## 執行方式

### 方式一：本地直接執行（靶機需先啟動）

```bash
# Step 1: 啟動靶機
docker compose up target-app -d

# Step 2: 等待靶機健康
docker compose wait target-app  # 或手動 curl 確認

# Step 3: 執行 Smoke Test（使用預設 localhost:8000）
k6 run engines/k6/smoke.js

# 指定自訂靶機 URL（e.g. 遠端測試機）
k6 run -e TARGET_URL=http://192.168.1.100:8000 engines/k6/smoke.js

# 輸出 JSON 報告（供後續分析）
k6 run engines/k6/smoke.js --out json=results/smoke_$(date +%Y%m%d_%H%M%S).json
```

### 方式二：透過 Docker 容器內的 Worker Agent 執行

```bash
# Step 1: 啟動完整生態系統
docker compose up -d

# Step 2: 向 Control Plane 建立 Smoke Test 任務
curl -s -X POST http://localhost:9000/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-PLoadtesting-Api-Token: dev-api-token-change-me" \
  -d '{
    "name": "smoke-test-health",
    "engine": "k6",
    "script_path": "k6/smoke.js",
    "target_url": "http://target-app:8000"
  }' | python3 -m json.tool

# Step 3: 查詢任務狀態（替換 {task_id}）
curl -s http://localhost:9000/api/tasks/{task_id}/ \
  -H "X-PLoadtesting-Api-Token: dev-api-token-change-me" | python3 -m json.tool
```

---

## 預期輸出（本地直接執行）

以下為靶機正常時 `k6 run engines/k6/smoke.js` 的**完整預期輸出**：

```

          /\      |‾‾| /‾‾/   /‾‾/
     /\  /  \     |  |/  /   /  /
    /  \/    \    |     (   /   ‾‾\
   /          \   |  |\  \ |  (‾)  |
  / __________ \  |__| \__\ \_____/ .io

  execution: local
     script: engines/k6/smoke.js
     output: -

  scenarios: (100.00%) 1 scenario, 1 max VUs, 40s max duration (incl. graceful stop):
           * default: 1 looping VUs for 10s (gracefulStop: 30s)


running (10.5s), 0/1 VUs, 9 complete and 0 interrupted iterations
default ✓ [======================================] 1 VUs  10s

     ✓ HTTP status is 200
     ✓ response body contains ok
     ✓ response time < 500ms

     checks.........................: 100.00% ✓ 27       ✗ 0
     data_received..................: 1.5 kB  143 B/s
     data_sent......................: 819 B   78 B/s
     error_rate.....................: 0.00%   ✓ 0        ✗ 0
   ✓ http_req_duration..............: avg=2.45ms  min=1.21ms  med=2.11ms  max=8.32ms  p(90)=4.23ms  p(95)=6.12ms  p(99)=8.32ms
       { expected_response:true }...: avg=2.45ms  min=1.21ms  med=2.11ms  max=8.32ms  p(90)=4.23ms  p(95)=6.12ms  p(99)=8.32ms
   ✓ http_req_failed................: 0.00%  ✓ 0        ✗ 9
     http_reqs......................: 9       0.857142/s
     iteration_duration.............: avg=1.00s   min=1.00s   med=1.00s   max=1.01s   p(90)=1.01s   p(95)=1.01s   p(99)=1.01s
     iterations.....................: 9       0.857142/s
     vus............................: 1       min=1       max=1
     vus_max........................: 1       min=1       max=1


running (10.5s), 0/1 VUs, 9 complete and 0 interrupted iterations
default ✓ [======================================] 1 VUs  10s
```

### 關鍵指標解讀

| 指標 | 預期值 | 說明 |
|---|---|---|
| `checks` | 100.00% ✓ | 所有 HTTP 狀態碼與回應內容驗證通過 |
| `http_req_failed` | 0.00% | 零失敗請求 |
| `http_req_duration p(99)` | < 500ms | 99% 請求在 500ms 內完成 |
| `error_rate` | 0.00% | 自訂失敗率為零 |
| `http_reqs` | ~9 次 | 10 秒 × 1 VU × 每次迭代 1 請求（含 1s sleep） |

### Threshold 判讀

- `✓` 前綴 = Threshold **通過**（測試健康）
- `✗` 前綴 = Threshold **失敗**（需排查問題）

---

## ❌ 常見錯誤排除

### 錯誤 1：`ECONNREFUSED` — 靶機未啟動

```
WARN[0000] Request Failed  error="Get \"http://localhost:8000/api/health\": dial tcp 127.0.0.1:8000: connect: connection refused"
```

**解決方式**：
```bash
docker compose up target-app -d
curl http://localhost:8000/api/health  # 確認回傳 {"status":"ok"}
```

---

### 錯誤 2：`k6: command not found`

**解決方式**：依照上方「前置條件」安裝 k6。

---

### 錯誤 3：Threshold 失敗（`✗ http_req_duration`）

```
✗ http_req_duration.............: ... p(99)=1234.56ms
```

**可能原因**：
1. 靶機容器資源限制（CPU throttling）— 確認 `docker stats`
2. 本機 CPU 高負載 — 關閉其他高耗能進程後重試
3. 網路問題（若連接遠端靶機）— 確認網路延遲

---

### 錯誤 4：Docker 環境下 `target-app` 無法解析

```
dial tcp: lookup target-app: no such host
```

**解決方式**：確認 k6 腳本使用 Docker 內部 hostname，不是 `localhost`：
```bash
k6 run -e TARGET_URL=http://target-app:8000 engines/k6/smoke.js
```

---

## 相關腳本

| 腳本 | 說明 | 使用時機 |
|---|---|---|
| `engines/k6/smoke.js` | 輕量存活確認，1 VU × 10s | **所有壓測前必跑** |
| `engines/k6/stress_cpu.js` | CPU 密集壓測，多 VU × 多分鐘 | 確認 CPU 處理能力 |
| `engines/k6/stress_io.js` | I/O 密集壓測，模擬高並發等待 | 確認非同步吞吐量 |
| `engines/k6/stress_data.js` | 大資料序列化壓測 | 確認網路頻寬與序列化效能 |
