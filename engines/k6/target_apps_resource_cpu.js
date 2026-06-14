import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 10 },
    { duration: '20s', target: 10 },
  ],
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18083';
const ITERATIONS = __ENV.CPU_ITERATIONS || '250000';

export default function () {
  const response = http.get(`${BASE_URL}/api/cpu?iterations=${ITERATIONS}`);
  check(response, {
    'resource cpu status is 200': (r) => r.status === 200,
    'resource cpu has checksum': (r) => typeof r.json('checksum') === 'number',
  });
}

