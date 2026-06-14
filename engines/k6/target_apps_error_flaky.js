import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 5,
  duration: '15s',
  thresholds: {
    http_req_duration: ['p(95)<1000'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18082';
const RATE = __ENV.FLAKY_RATE || '0.5';
const REQUEST_KEY = __ENV.FLAKY_REQUEST_KEY || 'ci';

export default function () {
  const response = http.get(
    `${BASE_URL}/api/flaky?rate=${RATE}&deterministic=true&request_key=${encodeURIComponent(REQUEST_KEY)}`
  );
  check(response, {
    'flaky result is deterministic terminal status': (r) => [200, 503].includes(r.status),
  });
}

