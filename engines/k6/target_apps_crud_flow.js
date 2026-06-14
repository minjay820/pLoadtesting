import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 5,
  duration: '20s',
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<1500'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18085';
const ITEM_NAME = __ENV.ITEM_NAME || 'demo-item';
const ITEM_VALUE = Number(__ENV.ITEM_VALUE || '42');

export default function () {
  const createResponse = http.post(
    `${BASE_URL}/api/items`,
    JSON.stringify({ name: ITEM_NAME, value: ITEM_VALUE }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(createResponse, {
    'crud create returns 201': (r) => r.status === 201,
  });

  const itemId = createResponse.json('id');
  const getResponse = http.get(`${BASE_URL}/api/items/${itemId}`);
  check(getResponse, {
    'crud get returns 200': (r) => r.status === 200,
    'crud get returns same id': (r) => r.json('id') === itemId,
  });
}

