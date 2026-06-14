import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 3,
  iterations: 4,
  thresholds: {
    http_req_duration: ['p(95)<2500'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:18086';
const USERNAME = __ENV.DEMO_USERNAME || 'alice';
const PASSWORD = __ENV.DEMO_PASSWORD || 'demo-password';
const ACCESS_TOKEN_USES = Number(__ENV.ACCESS_TOKEN_USES || '1');
const REFRESH_USES = Number(__ENV.REFRESH_USES || '2');
const ASSERT_FAILURE_BRANCHES = __ENV.ASSERT_FAILURE_BRANCHES === '1';

export default function () {
  if (ASSERT_FAILURE_BRANCHES) {
    const badLogin = http.post(
      `${BASE_URL}/api/login`,
      JSON.stringify({ username: USERNAME, password: 'bad-password' }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    check(badLogin, {
      'bad login is rejected': (r) => r.status === 401,
    });
  }

  const login = http.post(
    `${BASE_URL}/api/login`,
    JSON.stringify({
      username: USERNAME,
      password: PASSWORD,
      access_token_uses: ACCESS_TOKEN_USES,
      refresh_uses: REFRESH_USES,
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(login, { 'login ok': (r) => r.status === 200 });

  const accessToken = login.json('access_token');
  const refreshToken = login.json('refresh_token');
  const authHeaders = { headers: { Authorization: `Bearer ${accessToken}` } };

  const firstProfile = http.get(`${BASE_URL}/api/profile`, authHeaders);
  check(firstProfile, { 'initial profile ok': (r) => r.status === 200 });

  const expiredProfile = http.get(`${BASE_URL}/api/profile`, authHeaders);
  check(expiredProfile, { 'expired profile rejected': (r) => r.status === 401 });

  const refresh = http.post(
    `${BASE_URL}/api/refresh`,
    JSON.stringify({ refresh_token: refreshToken, access_token_uses: ACCESS_TOKEN_USES + 1 }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(refresh, { 'refresh ok': (r) => r.status === 200 });

  const refreshedAccessToken = refresh.json('access_token');
  const refreshedHeaders = { headers: { Authorization: `Bearer ${refreshedAccessToken}`, 'Content-Type': 'application/json' } };
  const refreshedProfile = http.get(`${BASE_URL}/api/profile`, refreshedHeaders);
  check(refreshedProfile, { 'refreshed profile ok': (r) => r.status === 200 });

  const logout = http.post(`${BASE_URL}/api/logout`, null, { headers: { Authorization: `Bearer ${refreshedAccessToken}` } });
  check(logout, { 'logout ok': (r) => r.status === 200 });

  const revokedProfile = http.get(`${BASE_URL}/api/profile`, { headers: { Authorization: `Bearer ${refreshedAccessToken}` } });
  check(revokedProfile, { 'revoked profile rejected': (r) => r.status === 401 });
}
