import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 2,
  iterations: 4,
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18089';

export default function () {
  const createPayload = JSON.stringify({
    name: __ENV.DB_RECORD_NAME || 'smoke-record',
    category: __ENV.DB_RECORD_CATEGORY || 'smoke',
    status: __ENV.DB_RECORD_STATUS || 'ready',
    value: Number(__ENV.DB_RECORD_VALUE || '17'),
  });

  const created = http.post(`${BASE_URL}/api/records`, createPayload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '5s',
  });

  check(created, {
    'db create status is 201': (r) => r.status === 201,
    'db create returns id': (r) => Number(r.json('id')) > 0,
  });

  const recordId = created.json('id');
  const fetched = http.get(`${BASE_URL}/api/records/${recordId}`, { timeout: '5s' });

  check(fetched, {
    'db fetch status is 200': (r) => r.status === 200,
    'db fetch returns created name': (r) => r.json('name') === (__ENV.DB_RECORD_NAME || 'smoke-record'),
  });
}
