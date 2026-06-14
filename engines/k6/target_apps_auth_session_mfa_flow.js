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
const FLOW_MODE = __ENV.FLOW_MODE || 'session';
const SESSION_USES = Number(__ENV.SESSION_USES || '2');
const MFA_CHANNEL = __ENV.MFA_CHANNEL || 'sms';
const MFA_ISSUE_MODE = __ENV.MFA_ISSUE_MODE || 'bearer';

function expectedMfaCode(username, channel) {
  const text = `${username}|${channel}`;
  let total = 0;
  for (let index = 0; index < text.length; index += 1) {
    total += text.charCodeAt(index);
  }
  return String((total * 137) % 1000000).padStart(6, '0');
}

export default function () {
  if (FLOW_MODE === 'session') {
    const jar = http.cookieJar();
    const login = http.post(
      `${BASE_URL}/api/session/login`,
      JSON.stringify({ username: USERNAME, password: PASSWORD, session_uses: SESSION_USES }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    check(login, {
      'session login ok': (r) => r.status === 200,
      'session login set cookie': () => jar.cookiesForURL(BASE_URL).ploadtesting_demo_session !== undefined,
    });

    const profile = http.get(`${BASE_URL}/api/session/profile`);
    check(profile, {
      'session profile ok': (r) => r.status === 200,
    });

    const logout = http.post(`${BASE_URL}/api/session/logout`);
    check(logout, {
      'session logout ok': (r) => r.status === 200,
    });

    const revokedProfile = http.get(`${BASE_URL}/api/session/profile`);
    check(revokedProfile, {
      'revoked session rejected': (r) => r.status === 401,
    });
    return;
  }

  const start = http.post(
    `${BASE_URL}/api/mfa/login/start`,
    JSON.stringify({ username: USERNAME, password: PASSWORD, channel: MFA_CHANNEL }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(start, {
    'mfa start ok': (r) => r.status === 200,
  });

  const challengeId = start.json('challenge_id');
  const code = expectedMfaCode(USERNAME, MFA_CHANNEL);
  const verify = http.post(
    `${BASE_URL}/api/mfa/login/verify`,
    JSON.stringify({
      challenge_id: challengeId,
      code,
      issue_mode: MFA_ISSUE_MODE,
      access_token_uses: 2,
      refresh_uses: 1,
      session_uses: 2,
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(verify, {
    'mfa verify ok': (r) => r.status === 200,
  });

  if (MFA_ISSUE_MODE === 'session') {
    const sessionProfile = http.get(`${BASE_URL}/api/session/profile`);
    check(sessionProfile, {
      'mfa session profile ok': (r) => r.status === 200,
    });
    return;
  }

  const accessToken = verify.json('access_token');
  const profile = http.get(`${BASE_URL}/api/profile`, { headers: { Authorization: `Bearer ${accessToken}` } });
  check(profile, {
    'mfa bearer profile ok': (r) => r.status === 200,
  });
}
