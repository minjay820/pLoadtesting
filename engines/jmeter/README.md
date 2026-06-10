# ⚙️ engines/jmeter — JMeter 壓測引擎

本目錄存放 pLoadtesting 的 **Apache JMeter** 測試計畫，
對應 Target App 的四個 Endpoint，涵蓋健康檢查、CPU 壓力、I/O 壓力與資料序列化四種情境。

---

## 📁 目錄結構

```
engines/jmeter/
├── ploadtesting_test_plan.jmx   ← 主測試計畫（JMeter 5.5+ 相容）
├── reports/               ← 執行後自動產生（.gitignore 排除）
│   ├── results.jtl        ←   原始量測資料（CSV 格式）
│   └── html/              ←   HTML 視覺化報告
└── README.md              ← 本文件
```

---

## 🧵 Thread Group 規格一覽

| # | 名稱 | Endpoint | Threads | Ramp-up | Duration / Loop |
|:---:|---|---|:---:|:---:|:---:|
| TG1 | Smoke Test | `GET /api/health` | 1 | 1s | Loop × 5 |
| TG2 | CPU Stress | `GET /api/cpu-bound?n=1000000` | 50 | 30s | 60s |
| TG3 | I/O Stress | `GET /api/io-bound?delay=1.0` | 200 | 5s | 60s |
| TG4 | Data API | `POST /api/data` | 20 | 10s | 60s |

---

## 🚀 執行方式

### 前置需求

| 工具 | 版本要求 | 下載 |
|---|---|---|
| Apache JMeter | 5.5+ | https://jmeter.apache.org/download_jmeter.cgi |
| Java | 11+ | https://adoptium.net |

```bash
# 確認 JMeter 可執行
jmeter --version
```

---

### 1. 標準執行（Non-GUI CLI 模式，建議用於正式壓測）

> **重要**：正式壓測請務必使用 Non-GUI 模式，GUI 模式會消耗額外資源，導致量測數值失真。

```bash
# 在此目錄下執行
cd engines/jmeter

# 建立報告輸出目錄
mkdir -p reports/html

# 執行全部 Thread Groups，產出 JTL + HTML 報告
jmeter \
  -n \
  -t ploadtesting_test_plan.jmx \
  -l reports/results.jtl \
  -e \
  -o reports/html
```

**參數說明**

| 參數 | 說明 |
|---|---|
| `-n` | Non-GUI 模式（必須） |
| `-t <file>` | 指定測試計畫 `.jmx` |
| `-l <file>` | JTL 結果輸出路徑（原始量測資料） |
| `-e` | 執行結束後產生 HTML 報告 |
| `-o <dir>` | HTML 報告輸出目錄（**必須為空目錄**） |

執行完畢後，用瀏覽器開啟報告：

```bash
open reports/html/index.html   # macOS
xdg-open reports/html/index.html   # Linux
```

---

### 2. 覆寫靶機位址（CLI 變數注入）

測試計畫預設打 `localhost:8000`；若靶機部署在其他主機，可用 `-J` 覆寫：

```bash
jmeter -n \
  -t ploadtesting_test_plan.jmx \
  -l reports/results.jtl \
  -e -o reports/html \
  -JTARGET_HOST=192.168.1.100 \
  -JTARGET_PORT=8000
```

---

### 3. 僅執行單一 Thread Group

在 GUI 中將不需要的 Thread Group 停用（右鍵 → Disable），再存檔後執行 CLI。
或在 CLI 用 `--jmeterlogfile` 搭配 JMeter Property 控制：

```bash
# 範例：只執行 TG1 Smoke Test（先在 GUI 停用 TG2~TG4，存檔後執行）
jmeter -n -t ploadtesting_test_plan_smoke_only.jmx -l reports/smoke.jtl
```

---

### 4. 使用 Docker 執行（無需本機安裝 JMeter）

```bash
# 以官方 JMeter Docker 映像執行（justb4/jmeter 為社群常用映像）
docker run --rm \
  -v "$(pwd)":/workspace \
  -w /workspace \
  --network host \
  justb4/jmeter:5.5 \
  -n \
  -t ploadtesting_test_plan.jmx \
  -l reports/results.jtl \
  -e -o reports/html
```

> `--network host` 讓 JMeter 容器可直接存取 Host 上的 `localhost:8000`（Target App）。

---

### 5. 僅產生 HTML 報告（不重新壓測）

若已有 JTL 檔案，可單獨產生 HTML 報告：

```bash
jmeter -g reports/results.jtl -o reports/html_reregen
```

---

## 📊 HTML 報告關鍵指標說明

| 指標 | 說明 | 健康基準（參考） |
|---|---|---|
| **Throughput** | 每秒完成的請求數（RPS） | 越高越好 |
| **Average** | 平均回應時間（ms） | `< 500ms`（視 SLA 而定） |
| **90th pct** | 90% 請求的最大回應時間 | `< 1000ms` |
| **99th pct** | 99% 請求的最大回應時間 | `< 3000ms` |
| **Error %** | 請求失敗率 | `< 1%` |
| **Received KB/s** | 網路接收吞吐量 | 取決於 TG4 回傳資料量 |

---

## 🔧 常見問題

### Q1：執行時出現 `Error in NonGUIDriver java.lang.Exception: Could not open JTL file: 'reports/results.jtl'`

**原因**：`reports/` 目錄不存在。  
**解法**：`mkdir -p reports/html` 後再執行。

### Q2：出現 `An error occurred: Non empty output folder reports/html`

**原因**：`-o` 指定的 HTML 報告目錄已有舊資料。  
**解法**：`rm -rf reports/html && mkdir -p reports/html`

### Q3：TG3 I/O Stress 的 Active Threads 沒有達到 200

**原因**：Target App 連線逾時設定（`response_timeout=30000ms`）與 JMeter Thread 啟動速度的競爭條件。  
**解法**：調整 JMeter 的 `HTTPSampler.response_timeout` 或縮短 `delay` 參數值。

### Q4：如何調整 `n` 或 `delay` 值而不修改 .jmx？

透過 JMeter 的 `__P()` 函式搭配 `-J` 參數（需在 .jmx 中先替換為函式語法）。
目前版本採靜態值，如需動態化請改用 `${__P(cpu_n,1000000)}` 語法。

---

## 📄 .gitignore 建議

```gitignore
# 壓測產出物（報告與 JTL 量測資料）
engines/jmeter/reports/
```
