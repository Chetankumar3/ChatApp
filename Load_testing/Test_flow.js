// ─── K6 Load Test — Realistic User Flow ────────────────────────────────────
import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';
import exec from 'k6/execution';

const BASE_URL = 'http://16.112.64.12.nip.io/chatapp/api';

export const options = {
    stages: [
        { duration: '1m', target: 100 },
        { duration: '1m', target: 100 },
        { duration: '1m', target: 0 },
    ],
    gracefulRampDown: '2m',
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

function jitter() { sleep(Math.min(1, Math.random() * 5)); }

function authHeaders(token) {
    return { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } };
}

// 🔥 THE K6 SECRET: VU-Level State
// Variables declared here are isolated PER VIRTUAL USER, 
// but they persist across iterations for that specific VU!
let token = null;
let auth = null;
let userId = null;
let currentUsername = null;
const password = 'Loadtest@99';

// ─── Default Function ────────────────────────────────────────────────────────
export default function () {
    
    // ─── PHASE 1: ONE-TIME SETUP (Register & Login) ──────────────────────────
    // This block only runs if the VU doesn't have a token yet (Iteration 0).
    // If it fails, the iteration returns and tries again on the next loop.
    if (!token) {
        const vuId = exec.vu.idInTest;
        const rand = randomString(4); 
        currentUsername = `vu_${vuId}_${rand}`; 

        // 1. Register
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

        if (!check(registerRes, { 'register → status 200 or 400': (r) => r.status === 200 || r.status === 400 })) return;
        jitter();

        // 2. Login
        const loginRes = http.post(
            `${BASE_URL}/login/credentials`,
            JSON.stringify({ username: currentUsername, password }),
            { headers: { 'Content-Type': 'application/json' } }
        );

        if (!check(loginRes, { 'login → status 200': (r) => r.status === 200 })) return;

        // 3. Save state to the outer variables
        const tempToken = loginRes.json('token');
        const payload = parseJWT(tempToken);
        if (!payload) return;

        token = tempToken;
        userId = payload.user_id;
        auth = authHeaders(token);
        jitter();
    }

    // ─── PHASE 2: CONTINUOUS LOAD (The 6 APIs) ───────────────────────────────
    // Because we survived the setup block, we now have a token. 
    // All subsequent iterations will skip Phase 1 and jump straight here!

    // 1. Get All Users
    check(http.get(`${BASE_URL}/get_all_users`, auth), {
        'get_all_users → status 200': (r) => r.status === 200,
    });
    jitter();

    // 2. Get User Info
    check(http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth), {
        'get_user_info → status 200': (r) => r.status === 200,
        'get_user_info → correct username': (r) => r.json('username') === currentUsername,
    });
    jitter();

    // 3. Get All Conversations
    check(http.get(`${BASE_URL}/users/get_all_conversations/${userId}`, auth), {
        'get_all_conversations → status 200': (r) => r.status === 200,
    });
    jitter();

    // 4. Change Username
    const newUsername = `vur_${randomString(10)}`;
    const changeRes = http.post(
        `${BASE_URL}/users/change_username/${userId}`,
        JSON.stringify({ newUsername }),
        auth
    );
    
    // 🔥 If the rename succeeds, update our VU-level state!
    if (check(changeRes, { 'change_username → status 200': (r) => r.status === 200 })) {
        currentUsername = newUsername; 
    }

    // 5. Verify rename persisted
    check(http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth), {
        'change_username → verify updated': (r) => r.json('username') === currentUsername,
    });
    
    jitter();
}