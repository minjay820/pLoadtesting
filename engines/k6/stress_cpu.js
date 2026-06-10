/**
 * nebula-load-tester — k6 CPU Stress Test
 * ==========================================
 * 目標端點：GET /api/cpu-bound?n=1000000
 * 目的：模擬 CPU 密集型高並發，量測 Throughput 與 Response Time 的壓力極限。
 *
 * 執行情境 (Stages)：
 *   0s  → 30s  ramp-up：0 → 50 VUs（模擬使用者逐步湧入）
 *   30s → 90s  sustain： 50 VUs（穩態壓測 60 秒，收集代表性數據）
 *   90s → 100s ramp-down：50 → 0 VUs（讓連線優雅關閉）
 *
 * Thresholds：
 *   - p(95) 回應時間 < 2000ms
 *   - 錯誤率 < 5%
 *
 * 用法：
 *   k6 run stress_cpu.js
 *   k6 run stress_cpu.js --out json=results/stress_cpu.json
 *   k6 run -e TARGET_URL=http://192.168.1.100:8000 stress_cpu.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── 自訂指標 ─────────────────────────────────────────────────────────────────
const errorRate   = new Rate('cpu_error_rate');
/** 記錄 API 回傳的伺服器端 CPU 實際耗時（elapsed_ms），與客戶端量測分離 */
const serverElapsed = new Trend('cpu_server_elapsed_ms', true);

// ─── 測試設定 ─────────────────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '30s', target: 50 }, // ramp-up：0 → 50 VUs
    { duration: '60s', target: 50 }, // sustain：維持 50 VUs 60 秒
    { duration: '10s', target: 0  }, // ramp-down：50 → 0 VUs
  ],

  thresholds: {
    // 95% 請求的端對端回應時間必須 < 2000ms
    http_req_duration:  ['p(95)<2000'],
    // HTTP 請求失敗率 < 5%（容許少量 503 等暫態錯誤）
    http_req_failed:    ['rate<0.05'],
    // 自訂：CPU 壓測錯誤率 < 5%
    cpu_error_rate:     ['rate<0.05'],
  },
};

// ─── 靶機 Base URL ────────────────────────────────────────────────────────────
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// ─── HTTP 請求參數（固定不變，提升效能） ──────────────────────────────────────
const params = {
  tags:    { name: 'GET /api/cpu-bound' },
  timeout: '30s', // 單次請求逾時（CPU-bound 可能需較長時間）
};

// ─── 主測試函式 ───────────────────────────────────────────────────────────────
export default function () {
  const res = http.get(`${BASE_URL}/api/cpu-bound?n=1000000`, params);

  const ok = check(res, {
    'HTTP status is 200':            (r) => r.status === 200,
    'response has elapsed_ms field': (r) => {
      try { return typeof r.json('elapsed_ms') === 'number'; }
      catch { return false; }
    },
  });

  errorRate.add(!ok);

  // 記錄伺服器端 CPU 計算耗時（區別於網路延遲）
  if (ok) {
    try {
      serverElapsed.add(res.json('elapsed_ms'));
    } catch (_) {
      // 忽略解析錯誤（避免 check 通過但 json 解析失敗的邊緣情況）
    }
  }

  // CPU-bound 請求本身已有 ~100ms 延遲，迭代間不需額外 sleep
}
