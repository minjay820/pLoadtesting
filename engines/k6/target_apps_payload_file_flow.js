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
const FILE_ENDPOINT_PATH = __ENV.FILE_ENDPOINT_PATH || '/api/files/fixture-1';
const FILE_KB = __ENV.FILE_KB || '32';
const FILE_DISPOSITION = __ENV.FILE_DISPOSITION || 'attachment';
const FILE_UPLOAD_MODE = __ENV.FILE_UPLOAD_MODE === '1';

export default function () {
  const manifest = http.get(`${BASE_URL}/api/files/manifest?count=3&kb_per_file=${FILE_KB}`, { timeout: '5s' });
  check(manifest, {
    'file manifest status is 200': (r) => r.status === 200,
    'file manifest has files': (r) => Array.isArray(r.json('files')) && r.json('files').length === 3,
  });

  const download = http.get(
    `${BASE_URL}${FILE_ENDPOINT_PATH}?kb=${FILE_KB}&disposition=${FILE_DISPOSITION}`,
    { responseType: 'binary', timeout: '5s' }
  );
  check(download, {
    'file download status is 200': (r) => r.status === 200,
    'file download content-disposition exists': (r) => String(r.headers['Content-Disposition'] || '').includes(FILE_DISPOSITION),
    'file download size matches': (r) => r.body && r.body.byteLength === Number(FILE_KB) * 1024,
  });

  if (FILE_UPLOAD_MODE) {
    const upload = http.post(
      `${BASE_URL}/api/files/upload?filename=roundtrip.bin`,
      download.body,
      {
        headers: { 'Content-Type': 'application/octet-stream' },
        timeout: '5s',
      }
    );
    check(upload, {
      'file upload status is 200': (r) => r.status === 200,
      'file upload bytes echoed': (r) => Number(r.json('received_bytes')) === Number(FILE_KB) * 1024,
    });
  }
}
