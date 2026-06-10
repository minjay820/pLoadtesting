/**
 * pLoadtesting — k6 Smoke Test
 * ====================================
 * 目標端點：GET /api/health
 * 目的：輕量確認服務存活，作為所有正式壓測前的 pre-flight 檢查。
 *
 * 執行參數：
 *   1 VU，持續 10 秒
 *
 * 用法：
 *   k6 run smoke.js
 *   k6 run smoke.js --out json=results/smoke.json
 *   k6 run -e TARGET_URL=http://192.168.1.100:8000 smoke.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// ─── 自訂指標 ────────────────────────────────────────────────────────────────
/** 請求失敗率（用於 Threshold 斷言） */
const errorRate = new Rate('error_rate');

// ─── 測試設定 ─────────────────────────────────────────────────────────────────
export const options = {
  // 1 VU，持續 10 秒
  vus: 1,
  duration: '10s',

  thresholds: {
    // HTTP 請求失敗率必須為 0%
    http_req_failed: ['rate==0'],
    // 99% 請求的回應時間必須 < 500ms（health check 應極快）
    http_req_duration: ['p(99)<500'],
    // 自訂失敗率 0%
    error_rate: ['rate==0'],
  },
};

// ─── 靶機 Base URL（透過環境變數動態注入） ────────────────────────────────────
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// ─── 主測試函式（每個 VU 每次迭代執行一次） ────────────────────────────────────
export default function () {
  const res = http.get(`${BASE_URL}/api/health`, {
    tags: { name: 'GET /api/health' }, // 在報告中顯示友善名稱
  });

  // ── check：同時驗證 HTTP 狀態碼與回應內容 ──
  const success = check(res, {
    'HTTP status is 200':        (r) => r.status === 200,
    'response body contains ok': (r) => r.json('status') === 'ok',
    'response time < 500ms':     (r) => r.timings.duration < 500,
  });

  // 更新自訂失敗率指標
  errorRate.add(!success);

  // 每次迭代後等待 1 秒，避免對健康檢查 endpoint 產生不必要的高頻打擊
  sleep(1);
}
