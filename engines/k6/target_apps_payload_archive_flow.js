import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 3,
  iterations: 4,
  thresholds: {
    http_req_failed: ['rate==0'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18084';
const PACK_COUNT = __ENV.PACK_COUNT || '4';
const PACK_KB_PER_FILE = __ENV.PACK_KB_PER_FILE || '12';

export default function () {
  const fixturePack = http.get(
    `${BASE_URL}/api/files/fixture-pack?count=${PACK_COUNT}&kb_per_file=${PACK_KB_PER_FILE}`,
    { timeout: '5s' }
  );
  check(fixturePack, {
    'fixture pack status is 200': (r) => r.status === 200,
    'fixture pack count matches': (r) => Number(r.json('count')) === Number(PACK_COUNT),
    'fixture pack files exist': (r) => Array.isArray(r.json('files')) && r.json('files').length === Number(PACK_COUNT),
  });

  const archive = http.get(
    `${BASE_URL}/api/files/archive?count=${PACK_COUNT}&kb_per_file=${PACK_KB_PER_FILE}`,
    { responseType: 'binary', timeout: '5s' }
  );
  check(archive, {
    'archive status is 200': (r) => r.status === 200,
    'archive content-type is zip': (r) => String(r.headers['Content-Type'] || '').includes('application/zip'),
    'archive has bytes': (r) => r.body && r.body.byteLength > Number(PACK_COUNT) * 128,
  });

  const readMany = http.get(
    `${BASE_URL}/api/files/read-many?count=${PACK_COUNT}&kb_per_file=${PACK_KB_PER_FILE}`,
    { timeout: '5s' }
  );
  check(readMany, {
    'read-many status is 200': (r) => r.status === 200,
    'read-many count matches': (r) => Number(r.json('count')) === Number(PACK_COUNT),
    'read-many total bytes positive': (r) => Number(r.json('total_bytes')) > 0,
    'read-many checksum exists': (r) => String(r.json('combined_sha256_prefix') || '').length === 16,
  });
}
