import http from 'k6/http';
import { check } from 'k6';
import { executionOptions } from './lib/execution.js';

export const options = executionOptions({
  vus: 10,
  durationSeconds: 20,
  rampUpSeconds: 10,
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<1500'],
  },
});

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18081';
const DELAY_MS = __ENV.DELAY_MS || '250';

export default function () {
  const response = http.get(`${BASE_URL}/api/delay/${DELAY_MS}`);
  check(response, {
    'delay status is 200': (r) => r.status === 200,
    'delay value matches': (r) => r.json('applied_delay_ms') === Number(DELAY_MS),
  });
}
