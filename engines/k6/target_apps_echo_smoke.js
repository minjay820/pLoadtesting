import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,
  duration: '10s',
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<500'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18080';
const MESSAGE = __ENV.ECHO_MESSAGE || 'smoke';
const REPEAT = __ENV.ECHO_REPEAT || '1';

export default function () {
  const response = http.get(`${BASE_URL}/api/echo?message=${encodeURIComponent(MESSAGE)}&repeat=${REPEAT}`);
  check(response, {
    'echo status is 200': (r) => r.status === 200,
    'echo payload contains message': (r) => r.json('message') === MESSAGE,
  });
  sleep(1);
}

