import http from 'k6/http';
import { check } from 'k6';
import { executionOptions } from './lib/execution.js';

export const options = executionOptions({
  vus: 2,
  durationSeconds: 10,
  iterations: 4,
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<2000'],
  },
});

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18084';
const PAYLOAD_KB = __ENV.PAYLOAD_KB || '32';

export default function () {
  const response = http.get(`${BASE_URL}/api/download?kb=${PAYLOAD_KB}`, { timeout: '5s' });
  const expectedBytes = Number(PAYLOAD_KB) * 1024;

  check(response, {
    'payload download status is 200': (r) => r.status === 200,
    'payload download content type is text': (r) => String(r.headers['Content-Type'] || '').includes('text/plain'),
    'payload download kb header matches': (r) => r.headers['X-Payload-KB'] === PAYLOAD_KB,
    'payload download size matches': (r) => r.body && r.body.length === expectedBytes,
  });
}
