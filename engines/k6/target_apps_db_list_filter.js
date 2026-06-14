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
const CATEGORY = __ENV.DB_LIST_CATEGORY || 'sales';
const STATUS = __ENV.DB_LIST_STATUS || 'ready';
const LIMIT = __ENV.DB_LIST_LIMIT || '10';

export default function () {
  const response = http.get(
    `${BASE_URL}/api/records?category=${CATEGORY}&status=${STATUS}&limit=${LIMIT}&sort_by=id&sort_order=asc`,
    { timeout: '5s' }
  );

  check(response, {
    'db list status is 200': (r) => r.status === 200,
    'db list count is bounded': (r) => Number(r.json('count')) <= Number(LIMIT),
    'db list items array exists': (r) => Array.isArray(r.json('items')),
  });
}
