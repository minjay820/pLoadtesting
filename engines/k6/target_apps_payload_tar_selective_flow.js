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

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18084';
const PACK_COUNT = Number(__ENV.PACK_COUNT || '5');
const PACK_KB_PER_FILE = Number(__ENV.PACK_KB_PER_FILE || '10');
const SELECTIVE_COUNT = Number(__ENV.SELECTIVE_COUNT || '3');

export default function () {
  const manifest = http.get(
    `${BASE_URL}/api/files/manifest?count=${PACK_COUNT}&kb_per_file=${PACK_KB_PER_FILE}`,
    { timeout: '5s' }
  );
  check(manifest, {
    'tar selective manifest status is 200': (r) => r.status === 200,
    'tar selective manifest has enough files': (r) => Array.isArray(r.json('files')) && r.json('files').length >= SELECTIVE_COUNT,
  });

  const selectedFiles = manifest.json('files').slice(0, SELECTIVE_COUNT);
  const selectedIds = selectedFiles.map((row) => row.file_id);
  const selectiveFetch = http.post(
    `${BASE_URL}/api/files/selective-fetch`,
    JSON.stringify({ file_ids: selectedIds, kb_per_file: PACK_KB_PER_FILE }),
    {
      headers: { 'Content-Type': 'application/json' },
      timeout: '5s',
    }
  );
  check(selectiveFetch, {
    'selective fetch status is 200': (r) => r.status === 200,
    'selective fetch count matches': (r) => Number(r.json('selected_count')) === SELECTIVE_COUNT,
    'selective fetch checksum exists': (r) => String(r.json('combined_sha256_prefix') || '').length === 16,
  });

  const tarQuery = selectedIds.map((fileId) => `file_ids=${encodeURIComponent(fileId)}`).join('&');
  const tarPackage = http.get(
    `${BASE_URL}/api/files/tar-package?${tarQuery}&kb_per_file=${PACK_KB_PER_FILE}`,
    { responseType: 'binary', timeout: '5s' }
  );
  check(tarPackage, {
    'tar package status is 200': (r) => r.status === 200,
    'tar package content-type is x-tar': (r) => String(r.headers['Content-Type'] || '').includes('application/x-tar'),
    'tar package has bytes': (r) => r.body && r.body.byteLength > SELECTIVE_COUNT * 256,
  });
}
