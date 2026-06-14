import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 1,
  iterations: 3,
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<5000'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18087';
const SSE_ENDPOINT_PATH = __ENV.SSE_ENDPOINT_PATH || '/api/events';
const SSE_COUNT = __ENV.SSE_COUNT || __ENV.SSE_STEPS || '5';
const SSE_INTERVAL_MS = __ENV.SSE_INTERVAL_MS || '50';
const EXPECTED_EVENT = SSE_ENDPOINT_PATH.includes('ticker')
  ? 'event: ticker'
  : SSE_ENDPOINT_PATH.includes('progress-heavy')
    ? 'event: progress-heavy'
  : SSE_ENDPOINT_PATH.includes('progress')
    ? 'event: progress'
    : 'event: message';
const COUNT_PARAM = SSE_ENDPOINT_PATH.includes('progress') ? 'steps' : 'count';

export default function () {
  const response = http.get(
    `${BASE_URL}${SSE_ENDPOINT_PATH}?${COUNT_PARAM}=${SSE_COUNT}&interval_ms=${SSE_INTERVAL_MS}&deterministic=true`,
    { timeout: '10s' }
  );

  check(response, {
    'sse status is 200': (r) => r.status === 200,
    'sse content-type is event-stream': (r) => String(r.headers['Content-Type'] || '').includes('text/event-stream'),
    'sse body contains expected event': (r) => r.body.includes(EXPECTED_EVENT),
    'sse body contains data lines': (r) => r.body.includes('data:'),
    'sse progress-heavy contains richer metadata': (r) =>
      !SSE_ENDPOINT_PATH.includes('progress-heavy') || (r.body.includes('"phase":"') && r.body.includes('"metrics":')),
  });
}
