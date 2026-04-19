// ─── K6 Load Test — Normal REST Flow ───────────────────────────────────────
// Flow: Register → Login → Get All Users → Get User Info → Get Conversations → Change Username
// Ramp: 0 → 1000 VUs over 1m │ Hold 1m │ Ramp down 1m

import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';


// ─── Environment ────────────────────────────────────────────────────────────
const BASE_URL = 'http://16.112.64.12/chatapp/api';

// ─── Stage Configuration ────────────────────────────────────────────────────
export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '10s', target: 100 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_failed: ['rate<0.05'],
        http_req_duration: ['p(95)<3000'],
    },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function parseJWT(token) {
  try {
    if (!token) return null;

    const parts = token.split('.');
    if (parts.length !== 3) return null;

    let base64 = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    while (base64.length % 4) base64 += '=';

    const decoded = encoding.b64decode(base64, 'std', 's'); // ✅ FIX
    return JSON.parse(decoded);

  } catch (e) {
    console.error('JWT parse error:', e.message);
    return null;
  }
}

function jitter() {
    sleep(Math.random() * 5);
}

function authHeaders(token) {
    return {
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
    };
}

// ─── Setup function to register the user ────────────────────────────────────
let username, password; // Declare globally to access in default function

export function setup() {
    const suffix = randomString(12);
    const username = `vu_${suffix}`;
    const password = 'Loadtest@99';

    // ── Register ──────────────────────────────────────────────────────────────
    const registerRes = http.post(
        `${BASE_URL}/recruiter/register`,
        JSON.stringify({
            username,
            password,
            name: `VU ${suffix}`,
            email: `${suffix}@loadtest.io`,
        }),
        { headers: { 'Content-Type': 'application/json' } }
    );

    if (
        !check(registerRes, {
            'register → status 200': (r) => r.status === 200,

            'register → has token': (r) => {
                if (!r.body) return false;           // avoid null body
                try {
                    return !!r.json('token');          // safe parse
                } catch (e) {
                    return false;                     // not JSON
                }
            },
        })
  ) return null;

    jitter();
    
    username = username;
    password = password;
}

// ─── Default Function ────────────────────────────────────────────────────────
export default function () {
    // ── Login ─────────────────────────────────────────────────────────────────
    const loginRes = http.post(
        `${BASE_URL}/login/credentials`,
        JSON.stringify({ username, password }),
        { headers: { 'Content-Type': 'application/json' } }
    );

    if (
        !check(loginRes, {
            'login → status 200': (r) => r.status === 200,
            'login → has token': (r) => !!r.json('token'),
        })
    ) return;

    const token = loginRes.json('token');
    const payload = parseJWT(token);
    if (!payload) return;

    const userId = payload.user_id;
    const auth = authHeaders(token);

    jitter();

    // ── Get All Users ─────────────────────────────────────────────────────────
    const allUsersRes = http.get(`${BASE_URL}/get_all_users`, auth);
    check(allUsersRes, {
        'get_all_users → status 200': (r) => r.status === 200,
        'get_all_users → users is array': (r) => Array.isArray(r.json('users')),
    });

    jitter();

    // ── Get User Info ─────────────────────────────────────────────────────────
    const userInfoRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
    check(userInfoRes, {
        'get_user_info → status 200': (r) => r.status === 200,
        'get_user_info → correct id': (r) => r.json('id') === userId,
        'get_user_info → has username': (r) => r.json('username') === username,
    });

    jitter();

    // ── Get All Conversations ─────────────────────────────────────────────────
    const convsRes = http.get(
        `${BASE_URL}/users/get_all_conversations/${userId}`,
        auth
    );
    check(convsRes, {
        'get_all_conversations → status 200': (r) => r.status === 200,
        'get_all_conversations → direct_messages': (r) => Array.isArray(r.json('direct_messages')),
        'get_all_conversations → associated_groups': (r) => Array.isArray(r.json('associated_groups')),
    });

    jitter();

    // ── Change Username ───────────────────────────────────────────────────────
    const newUsername = `vur_${randomString(10)}`;
    const changeRes = http.post(
        `${BASE_URL}/users/change_username/${userId}`,
        JSON.stringify({ newUsername }),
        auth
    );
    check(changeRes, {
        'change_username → status 200': (r) => r.status === 200,
    });
    username = newUsername;

    // Verify rename persisted
    const verifyRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
    check(verifyRes, {
        'change_username → verify updated': (r) => r.json('username') === newUsername,
    });

    jitter();
}