// ─── K6 Load Test — Fully Isolated State ────────────────────────────────────
import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';
import exec from 'k6/execution'; // 🔥 New: Access VU execution context

const BASE_URL = 'http://16.112.64.12/chatapp/api';

export const options = {
    stages: [
        { duration: '1m', target: 100 }, // Ramp up to 100
        { duration: '1m', target: 100 }, // Hold at 100
        { duration: '1m', target: 0 },   // Ramp down to 0
    ],
    
    // 🔥 Tell k6 to wait up to 2 full minutes for VUs to finish 
    // their current loop during the ramp-down phase.
    gracefulRampDown: '2m', 
    
    // 🔥 Tell k6 to wait up to 2 full minutes for any remaining VUs 
    // to finish before completely shutting down the entire test.
    gracefulStop: '2m',     

    thresholds: {
        http_req_failed: ['rate<0.05'],
        http_req_duration: ['p(95)<3000'],
    },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function parseJWT(token) {
    if (!token) return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) base64 += '=';
    return JSON.parse(encoding.b64decode(base64, 'std', 's'));
}

function jitter() { sleep( Math.min(1, Math.random() * 5)); }

function authHeaders(token) {
    return { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } };
}

// ─── Default Function ────────────────────────────────────────────────────────
export default function () {
    // 1. GENERATE UNIQUE IDENTITY (Strictly under 20 chars)
    // Example: vu_10_i5_abcd (13 chars max usually)
    const vuId = exec.vu.idInTest;
    const iter = exec.vu.iterationInInstance;
    const rand = randomString(4); 
    
    let currentUsername = `vu_${vuId}_i${iter}_${rand}`; 
    const password = 'Loadtest@99';

    // ── Register ──────────────────────────────────────────────────────────────
    const registerRes = http.post(
        `${BASE_URL}/register`,
        JSON.stringify({
            username: currentUsername,
            password: password,
            name: `VU ${vuId}`,
            email: `${currentUsername}@loadtest.io`,
        }),
        { headers: { 'Content-Type': 'application/json' } }
    );

    if (!check(registerRes, { 'register → status 200': (r) => r.status === 200 })) return;
    jitter();

    // ── Login ─────────────────────────────────────────────────────────────────
    const loginRes = http.post(
        `${BASE_URL}/login/credentials`,
        JSON.stringify({ username: currentUsername, password }),
        { headers: { 'Content-Type': 'application/json' } }
    );

    if (!check(loginRes, { 'login → status 200': (r) => r.status === 200 })) return;

    const token = loginRes.json('token');
    const payload = parseJWT(token);
    if (!payload) return;

    const userId = payload.user_id;
    const auth = authHeaders(token);
    jitter();

    // ── Get All Users ─────────────────────────────────────────────────────────
    check(http.get(`${BASE_URL}/get_all_users`, auth), {
        'get_all_users → status 200': (r) => r.status === 200,
    });
    jitter();

    // ── Get User Info ─────────────────────────────────────────────────────────
    check(http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth), {
        'get_user_info → status 200': (r) => r.status === 200,
        'get_user_info → correct username': (r) => r.json('username') === currentUsername,
    });
    jitter();

    // ── Get All Conversations ─────────────────────────────────────────────────
    check(http.get(`${BASE_URL}/users/get_all_conversations/${userId}`, auth), {
        'get_all_conversations → status 200': (r) => r.status === 200,
    });
    jitter();

    // ── Change Username ───────────────────────────────────────────────────────
    // Generates a totally fresh 14-character string (vur_ + 10 random chars)
    // Safely well below your VARCHAR(20) limit!
    const newUsername = `vur_${randomString(10)}`;
    
    const changeRes = http.post(
        `${BASE_URL}/users/change_username/${userId}`,
        JSON.stringify({ newUsername }),
        auth
    );
    
    if (check(changeRes, { 'change_username → status 200': (r) => r.status === 200 })) {
        currentUsername = newUsername; // Update local state for assertions
    }

    // Verify rename persisted
    check(http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth), {
        'change_username → verify updated': (r) => r.json('username') === currentUsername,
    });
    
    jitter();
}