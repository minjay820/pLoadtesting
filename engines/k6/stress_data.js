/**
 * pLoadtesting — k6 Data API Stress Test
 * ===============================================
 * 目標端點：POST /api/data
 * 目的：模擬高並發 JSON 序列化與網路頻寬壓力。
 *       每次回應約 8–12 KB，測試伺服器的記憶體分配與網路吞吐量。
 *
 * 執行情境 (Stages)：
 *   0s  → 10s  ramp-up：0 → 20 VUs（模擬使用者逐步湧入）
 *   10s → 70s  sustain： 20 VUs 維持 60 秒
 *
 * Thresholds：
 *   - p(95) 回應時間 < 1500ms
 *   - 錯誤率 < 1%
 *   - 回應資料量 > 5KB（確認 100 筆資料確實回傳）
 *
 * 用法：
 *   k6 run stress_data.js
 *   k6 run stress_data.js --out json=results/stress_data.json
 *   k6 run -e TARGET_URL=http://192.168.1.100:8000 stress_data.js
 */

import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── 自訂指標 ─────────────────────────────────────────────────────────────────
const errorRate      = new Rate('data_error_rate');
/** 追蹤每次回應的資料筆數，確認伺服器確實回傳 100 筆 */
const itemCountTrend = new Trend('data_item_count');

// ─── 測試設定 ─────────────────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '10s', target: 20 }, // ramp-up：0 → 20 VUs
    { duration: '60s', target: 20 }, // sustain：維持 20 VUs 60 秒
  ],

  thresholds: {
    // p(95) 端對端回應時間 < 1500ms
    http_req_duration: ['p(95)<1500'],
    // HTTP 層失敗率 < 1%
    http_req_failed:   ['rate<0.01'],
    // 自訂：Data API 錯誤率 < 1%
    data_error_rate:   ['rate<0.01'],
    // 自訂：回傳 item 數量應恆為 100（min == max == 100）
    data_item_count:   ['min==100', 'max==100'],
  },
};

// ─── 靶機 Base URL ────────────────────────────────────────────────────────────
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// ─── 預先序列化 Payload（避免每次迭代重新 JSON.stringify） ────────────────────
const PAYLOAD = JSON.stringify({ id: 1, payload: 'k6-test' });

// ─── 預先建立請求 Headers ─────────────────────────────────────────────────────
const HEADERS = {
  headers: { 'Content-Type': 'application/json' },
  tags:    { name: 'POST /api/data' },
  timeout: '30s',
};

// ─── 主測試函式 ───────────────────────────────────────────────────────────────
export default function () {
  const res = http.post(`${BASE_URL}/api/data`, PAYLOAD, HEADERS);

  // ── check 1：HTTP 狀態與資料結構 ──
  const structOk = check(res, {
    'HTTP status is 200':      (r) => r.status === 200,
    'response has count field': (r) => {
      try { return typeof r.json('count') === 'number'; }
      catch { return false; }
    },
    'response has items array': (r) => {
      try { return Array.isArray(r.json('items')); }
      catch { return false; }
    },
  });

  // ── check 2：業務邏輯驗證（count 必須為 100） ──
  let itemCount = 0;
  if (structOk) {
    try {
      itemCount = res.json('count');
    } catch (_) {
      // 忽略 JSON 解析邊緣情況
    }
  }

  const dataOk = check(res, {
    'count equals 100': () => itemCount === 100,
  });

  errorRate.add(!(structOk && dataOk));

  // 記錄每次回應的 item 數量到 Trend 指標
  if (itemCount > 0) {
    itemCountTrend.add(itemCount);
  }
}
