import http from 'k6/http';
import { check } from 'k6';
import { executionOptions } from './lib/execution.js';

export const options = executionOptions({
  vus: 5,
  durationSeconds: 20,
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<2000'],
  },
});

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18086';
const USERNAME = __ENV.DEMO_USERNAME || 'alice';
const PASSWORD = __ENV.DEMO_PASSWORD || 'demo-password';
const SKU = __ENV.DEMO_SKU || 'sku-1';
const QUANTITY = Number(__ENV.DEMO_QUANTITY || '1');

export default function () {
  const login = http.post(
    `${BASE_URL}/api/login`,
    JSON.stringify({ username: USERNAME, password: PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(login, { 'login ok': (r) => r.status === 200 });

  const token = login.json('access_token');
  const authHeaders = {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  };

  const profile = http.get(`${BASE_URL}/api/profile`, authHeaders);
  check(profile, { 'profile ok': (r) => r.status === 200 });

  const checkout = http.post(
    `${BASE_URL}/api/checkout`,
    JSON.stringify({ sku: SKU, quantity: QUANTITY }),
    authHeaders
  );
  check(checkout, { 'checkout ok': (r) => r.status === 200 });
}
