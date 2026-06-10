/**
 * pLoadtesting — k6 I/O Stress Test
 * ==========================================
 * 目標端點：GET /api/io-bound?delay=1.0
 * 目的：以 200 VUs 高並發驗證 FastAPI 非同步 Event Loop 的 I/O 能力。
 *       每個請求需等待 1 秒的 asyncio.sleep，
 *       理論 Throughput ≈ 200 req/s（若 Event Loop 真正非阻塞）。
 *
 * 執行情境 (Stages)：
 *   0s  → 0s   直接啟動：200 VUs（峰值湧入，測試瞬間連線承載能力）
 *   0s  → 60s  sustain： 200 VUs 維持 60 秒
 *
 * Thresholds：
 *   - p(95) 回應時間 < 3500ms（含 1s 延遲 + 500ms 容忍誤差 × 2.5 倍）
 *   - 錯誤率 < 1%
 *
 * 用法：
 *   k6 run stress_io.js
 *   k6 run stress_io.js --out json=results/stress_io.json
 *   k6 run -e TARGET_URL=http://192.168.1.100:8000 stress_io.js
 */

import http from 'k6/http';
import { check } from 'k6';
import { Rate } from 'k6/metrics';

// ─── 自訂指標 ─────────────────────────────────────────────────────────────────
const errorRate = new Rate('io_error_rate');

// ─── 測試設定 ─────────────────────────────────────────────────────────────────
export const options = {
  stages: [
    // 直接以 200 VUs 啟動：ramp-up 設為 0s，模擬瞬間流量峰值
    { duration: '0s',  target: 200 },
    // 維持 200 VUs 60 秒，收集穩態 I/O 並發數據
    { duration: '60s', target: 200 },
  ],

  thresholds: {
    // p(95) < 3500ms：1000ms 延遲 + 2000ms 系統開銷容忍 + 500ms 緩衝
    http_req_duration: ['p(95)<3500'],
    // HTTP 層級失敗率 < 1%
    http_req_failed:   ['rate<0.01'],
    // 自訂 I/O 壓測錯誤率 < 1%
    io_error_rate:     ['rate<0.01'],
  },
};

// ─── 靶機 Base URL ────────────────────────────────────────────────────────────
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// ─── 預先建立請求參數（避免每次迭代重新分配物件） ─────────────────────────────
const params = {
  tags:    { name: 'GET /api/io-bound' },
  // 逾時需大於 delay 參數（1.0s）加上合理的網路延遲緩衝
  timeout: '15s',
};

// ─── 主測試函式 ───────────────────────────────────────────────────────────────
export default function () {
  const res = http.get(`${BASE_URL}/api/io-bound?delay=1.0`, params);

  const ok = check(res, {
    'HTTP status is 200':               (r) => r.status === 200,
    'response body has delay field':    (r) => {
      try { return typeof r.json('delay') === 'number'; }
      catch { return false; }
    },
    'response time within expectation': (r) => r.timings.duration < 3500,
  });

  errorRate.add(!ok);

  // I/O-bound 請求本身已包含 1s 等待，不需額外 sleep
  // （讓 VU 盡快發起下一個請求，維持高並發壓力）
}
