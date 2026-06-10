# 🌌 nebula-load-tester

> **多引擎自動化壓測生態系統 (Multi-Engine Automated Load Testing Ecosystem)**

[![Phase](https://img.shields.io/badge/Phase-0%20Scaffolding-blueviolet)]()
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

---

## 📐 架構藍圖 (Architecture Blueprint)

```
                         ┌─────────────────────────────────────────┐
                         │           Control Plane (Web UI)         │
                         │  ┌──────────────┐  ┌──────────────────┐ │
                         │  │  Task Queue  │  │  Report Collector│ │
                         │  └──────┬───────┘  └────────┬─────────┘ │
                         └─────────┼────────────────────┼───────────┘
                                   │  dispatch           │  results
                    ┌──────────────┼──────────────────────┼────────────────┐
                    ▼              ▼                       ▼                ▼
             ┌──────────┐  ┌──────────┐           ┌──────────┐    ┌──────────┐
             │ Worker 1 │  │ Worker 2 │    ...     │ Worker N │    │  Worker  │
             │  (k6)    │  │(JMeter)  │            │  (LR)    │    │ (custom) │
             └────┬─────┘  └────┬─────┘           └────┬─────┘    └────┬─────┘
                  │              │                       │               │
                  └──────────────┴───────────────────────┴───────────────┘
                                             │
                                    HTTP / gRPC / WS
                                             │
                              ┌──────────────▼──────────────┐
                              │         Target App           │
                              │    (Reference API Server)    │
                              └─────────────────────────────┘
```

---

## 🗂️ 目錄結構說明 (Directory Structure)

```
nebula-load-tester/
│
├── target-app/               # 靶機應用程式
├── engines/                  # 壓測引擎腳本區
│   ├── k6/                   # k6 壓測腳本
│   ├── jmeter/               # JMeter 測試計畫
│   └── loadrunner/           # LoadRunner 腳本
│
├── control-plane/            # Web 中控平台
├── workers/                  # 遠端工作節點
├── docker-compose.yml        # 容器編排設定
└── README.md                 # 本文件
```

### 📦 target-app/

**用途**：提供一個可部署的「靶機」API 服務，作為所有壓測引擎的統一打靶目標。

| 規劃內容 | 說明 |
|---|---|
| 技術選型 | Node.js / FastAPI / Go（待定） |
| 端點設計 | `/health`、`/api/users`、`/api/orders` 等模擬真實業務場景的 endpoint |
| 可觀測性 | 內建 Prometheus metrics export (`/metrics`) |
| 部署方式 | Docker 容器，透過 `docker-compose` 一鍵啟動 |

---

### ⚙️ engines/

壓測腳本的核心倉庫，依引擎分類管理，每個子目錄自成一個獨立執行單元。

#### `engines/k6/`

**用途**：存放所有 [k6](https://k6.io) 壓測腳本（JavaScript）。

| 規劃內容 | 說明 |
|---|---|
| 腳本格式 | `.js` ES Modules |
| 情境分類 | `smoke/`、`load/`、`stress/`、`soak/`、`spike/` |
| 輸出整合 | k6 Cloud / InfluxDB + Grafana |
| 執行方式 | `k6 run engines/k6/<scenario>.js` |

#### `engines/jmeter/`

**用途**：存放 [Apache JMeter](https://jmeter.apache.org) 測試計畫（`.jmx`）與相關資源。

| 規劃內容 | 說明 |
|---|---|
| 腳本格式 | `.jmx` XML 測試計畫 |
| 參數化 | Properties files / CSV Data Sets |
| 分散式執行 | JMeter Master-Slave 模式設定 |
| 報表輸出 | HTML Report / JTL → Grafana |

#### `engines/loadrunner/`

**用途**：存放 [LoadRunner](https://www.microfocus.com/loadrunner) / LoadRunner Community Edition 腳本。

| 規劃內容 | 說明 |
|---|---|
| 腳本格式 | C-based VUser Scripts |
| 整合方式 | CLI 執行（`lr_start_scenario`）或 REST API 觸發 |
| 報表格式 | Analysis Summary / SLA 報告 |

---

### 🖥️ control-plane/

**用途**：提供 Web 介面的「中控台」，負責任務調度、Workers 管理及壓測結果彙整。

| 功能模塊 | 說明 |
|---|---|
| 任務調度 (Task Dispatcher) | 建立壓測任務、選擇引擎與場景、指派 Worker |
| Worker 管理 | 顯示在線節點、健康狀態、資源使用率 |
| 報告中心 | 彙整各 Worker 回傳的結果，產生統一視圖 |
| 設定管理 | Target App URL、通知設定（Slack / Email）、SLA 閾值 |
| 技術選型 | Next.js / React + Node.js API（待定） |

---

### 🤖 workers/

**用途**：部署於各測試節點的 Agent，接收來自 Control Plane 的指令，在本地執行對應的壓測引擎，並將結果串流回中控台。

| 功能模塊 | 說明 |
|---|---|
| 指令接收 | 監聽 Control Plane 的任務下發（WebSocket / HTTP Long-poll / gRPC） |
| 引擎執行 | 動態呼叫 k6 / JMeter / LoadRunner 執行對應腳本 |
| 結果回傳 | 即時串流日誌與最終報表 JSON 回中控台 |
| 自我健康回報 | 定期心跳（heartbeat）回報節點可用狀態 |
| 技術選型 | Go / Node.js（待定） |

---

## 🗓️ 開發階段規劃 (Development Phases)

| 階段 | 名稱 | 目標 | 狀態 |
|:---:|---|---|:---:|
| **Phase 0** | 專案鷹架 (Scaffolding) | 建立目錄結構、架構文件、docker-compose 外框 | ✅ **當前** |
| **Phase 1** | Target App | 實作靶機 API，提供 `/health`、`/api/*` 端點，內建 metrics | 🔜 |
| **Phase 2** | 引擎整合 (Engines) | 撰寫 k6 基礎場景腳本，驗證端對端壓測可行性 | 🔜 |
| **Phase 3** | Worker Agent | 實作 Worker 服務，支援本地執行 k6 並輸出結構化結果 | 🔜 |
| **Phase 4** | Control Plane MVP | 實作基礎 Web UI：任務建立、Worker 列表、結果查看 | 🔜 |
| **Phase 5** | 多引擎擴充 | 將 JMeter、LoadRunner 引擎納入 Worker 執行能力 | 🔜 |
| **Phase 6** | 可觀測性整合 | 串接 InfluxDB + Grafana，提供即時監控儀表板 | 🔜 |
| **Phase 7** | 分散式 Workers | 支援多節點水平擴展，Control Plane 實現負載均衡調度 | 🔜 |
| **Phase 8** | 生產強化 | CI/CD 整合、SLA 告警、完整 E2E 測試覆蓋 | 🔜 |

---

## 🛠️ 快速開始 (Quick Start)

> ⚠️ **Phase 0 注意**：目前僅有目錄骨架，尚無可執行服務。

```bash
# 1. Clone 專案
git clone <repo-url> nebula-load-tester
cd nebula-load-tester

# 2. （未來）啟動完整生態系統
docker-compose up -d

# 3. （未來）僅啟動靶機
docker-compose up target-app
```

---

## 🤝 貢獻指南 (Contributing)

- 每個 Phase 以獨立 Feature Branch 開發（`feat/phase-1-target-app`）
- 提交 PR 前請確保 `docker-compose up` 可正常啟動相關服務
- 壓測腳本請附上對應的 `README.md` 說明執行方式與預期 SLA 基準

---

## 📄 授權 (License)

MIT License © 2026 nebula-load-tester contributors
