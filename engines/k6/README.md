# ⚙️ engines/k6 — k6 壓測引擎

本目錄存放 nebula-load-tester 的 **[k6](https://k6.io)** 壓測腳本，
以 JavaScript (ES2015+) 撰寫，涵蓋四種壓測情境，對應 Target App 的四個端點。

---

## 📁 目錄結構

```
engines/k6/
├── smoke.js          ← 煙霧測試 (GET /api/health)
├── stress_cpu.js     ← CPU 密集壓測 (GET /api/cpu-bound)
├── stress_io.js      ← I/O 並發壓測 (GET /api/io-bound)
├── stress_data.js    ← 資料序列化壓測 (POST /api/data)
├── results/          ← 執行後自動產生（.gitignore 排除）
│   ├── smoke.json
│   ├── stress_cpu.json
│   ├── stress_io.json
│   └── stress_data.json
└── README.md         ← 本文件
```

---

## 🧵 腳本規格一覽

| 腳本 | 端點 | VUs | 情境 | Thresholds |
|---|---|:---:|---|---|
| `smoke.js` | `GET /api/health` | 1 | 持續 10s | p(99) < 500ms，錯誤率 = 0% |
| `stress_cpu.js` | `GET /api/cpu-bound?n=1000000` | 0→50→0 | 30s ramp + 60s + 10s down | p(95) < 2000ms，錯誤率 < 5% |
| `stress_io.js` | `GET /api/io-bound?delay=1.0` | 200 | 直接 200 VUs，60s | p(95) < 3500ms，錯誤率 < 1% |
| `stress_data.js` | `POST /api/data` | 0→20 | 10s ramp + 60s | p(95) < 1500ms，count 恆為 100 |

---

## 🚀 前置需求

```bash
# macOS（Homebrew）
brew install k6

# 確認版本（需 0.45+）
k6 version
```

其他安裝方式請參考 [k6 官方文件](https://k6.io/docs/get-started/installation/)。

---

## ▶️ 執行方式

### 1. 標準執行（打本機 Target App）

```bash
# 在此目錄執行
cd engines/k6

# 煙霧測試（確認服務存活）
k6 run smoke.js

# CPU 壓力測試
k6 run stress_cpu.js

# I/O 並發壓力測試
k6 run stress_io.js

# 資料 API 壓力測試
k6 run stress_data.js
```

---

### 2. 輸出 JSON 結果（供 Control Plane 讀取）⭐

> **重要**：`--out json` 是 Control Plane 整合的關鍵參數。
> 未來 Control Plane 將讀取此 JSON 報表，解析指標並呈現在 Web UI 上。

```bash
# 建立結果目錄
mkdir -p results

# 執行並輸出 JSON 結果（推薦格式）
k6 run smoke.js       --out json=results/smoke.json
k6 run stress_cpu.js  --out json=results/stress_cpu.json
k6 run stress_io.js   --out json=results/stress_io.json
k6 run stress_data.js --out json=results/stress_data.json
```

**JSON 輸出格式說明**：每行是一個獨立的 JSON 物件（JSON Lines 格式），
Control Plane 可逐行解析，支援即時串流讀取：

```jsonl
{"type":"Metric","data":{"name":"http_req_duration","type":"trend","contains":"time",...}}
{"type":"Point","data":{"metric":"http_req_duration","time":"...","value":142.5,...}}
```

---

### 3. 同時輸出多種格式

```bash
# 同時輸出 JSON（供 Control Plane）+ CSV（備份存檔）
k6 run stress_cpu.js \
  --out json=results/stress_cpu.json \
  --out csv=results/stress_cpu.csv
```

---

### 4. 覆寫靶機位址（環境變數注入）

所有腳本均讀取 `TARGET_URL` 環境變數，預設為 `http://localhost:8000`：

```bash
# 打遠端靶機
k6 run -e TARGET_URL=http://192.168.1.100:8000 stress_cpu.js

# 搭配 JSON 輸出
k6 run \
  -e TARGET_URL=http://staging.example.com:8000 \
  --out json=results/stress_cpu.json \
  stress_cpu.js
```

---

### 5. 調整 VUs / Duration（臨時覆寫，不修改腳本）

```bash
# 用 CLI 旗標覆寫腳本內的 options（僅適用於未設定 stages 的腳本）
k6 run --vus 5 --duration 30s smoke.js

# stress_cpu.js 使用 stages，可用 --stage 覆寫（k6 0.43+）
k6 run --stage 10s:10,30s:10,10s:0 stress_cpu.js
```

---

### 6. 使用 Docker 執行（無需本機安裝 k6）

```bash
# 掛載當前目錄，打本機 Target App
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  --network host \
  grafana/k6 run smoke.js

# 搭配 JSON 輸出
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  --network host \
  grafana/k6 run --out json=results/smoke.json smoke.js
```

---

## 📊 關鍵指標說明

| 指標名稱 | 說明 |
|---|---|
| `http_req_duration` | 端對端請求時間（含 DNS、TCP、伺服器處理、回傳） |
| `http_req_failed` | HTTP 4xx/5xx 的請求比率 |
| `http_reqs` | 總請求數與每秒請求數（RPS） |
| `vus` | 任意時刻的活躍 Virtual Users 數 |
| `cpu_server_elapsed_ms` | *(stress_cpu.js 專屬)* 伺服器端 CPU 計算耗時 |
| `data_item_count` | *(stress_data.js 專屬)* 每次回應的資料筆數 |
| `io_error_rate` / `cpu_error_rate` / `data_error_rate` | 各腳本自訂失敗率 |

---

## 🔧 Threshold 失敗時的處理

k6 在 Threshold 未通過時會以 **exit code 99** 結束，CI/CD 可直接捕捉：

```bash
k6 run stress_cpu.js --out json=results/stress_cpu.json
if [ $? -ne 0 ]; then
  echo "❌ Threshold 未通過，壓測失敗"
  exit 1
fi
echo "✅ 壓測通過所有 Thresholds"
```

---

## 📄 .gitignore 建議

```gitignore
# k6 壓測結果
engines/k6/results/
```
