import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';
import exec from 'k6/execution';

const BASE_URL = 'http://16.112.64.12.nip.io/chatapp/api';

export const options = {
    stages: [
        { duration: '5m', target: 1000 },
        { duration: '5m', target: 1000 },
        { duration: '2m', target: 0 },
    ],
    gracefulRampDown: '1m',
    gracefulStop: '1m',
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

// ─── VU State Variables ──────────────────────────────────────────────────────
// These variables persist across iterations for the same Virtual User
let isSetupComplete = false;
let token = null;
let auth = null;
let userId = null;
let currentUsername = null;
const password = 'Loadtest@99';

// ─── Default Function ────────────────────────────────────────────────────────
export default function () {
    
    // ─── PHASE 1: ONE-TIME SETUP (REGISTER & LOGIN) ──────────────────────────
    if (!isSetupComplete) {
        const vuId = exec.vu.idInTest;
        
        // 1. Generate Username with "Test" prefix to bypass CPU-heavy bcrypt
        currentUsername = `Test_vu${vuId}_${randomString(6)}`;

        // 2. Register
        const regPayload = JSON.stringify({
            username: currentUsername,
            password: password,
            name: `Load Test User ${vuId}`,
            email: `${currentUsername}@loadtest.io`,
        });

        const regRes = http.post(`${BASE_URL}/register`, regPayload, { 
            headers: { 'Content-Type': 'application/json' } 
        });
        
        // If registration fails, exit the iteration early to try again
        if (!check(regRes, { 'register → status 200': (r) => r.status === 200 })) {
            sleep(1);
            return;
        }

        // 3. Login
        const loginPayload = JSON.stringify({ username: currentUsername, password: password });
        const loginRes = http.post(`${BASE_URL}/login/credentials`, loginPayload, { 
            headers: { 'Content-Type': 'application/json' } 
        });

        if (check(loginRes, { 'login → status 200': (r) => r.status === 200 })) {
            token = loginRes.json('token');
            const payload = parseJWT(token);
            if (payload) {
                userId = payload.user_id;
                auth = authHeaders(token);
                isSetupComplete = true; // Mark complete so this VU skips setup on next iteration
            }
        } else {
            sleep(1);
            return;
        }
        sleep(1);
    }

    // ─── PHASE 2: CONTINUOUS LOAD ────────────────────────────────────────────

    // 1. Get All Users
    const getAllRes = http.get(`${BASE_URL}/get_all_users`, auth);
    check(getAllRes, { 'get_all_users → status 200': (r) => r.status === 200 });
    jitter();

    // 2. Get User Info
    const getUserRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
    check(getUserRes, { 
        'get_user_info → status 200': (r) => r.status === 200,
        'get_user_info → correct username': (r) => r.json('username') === currentUsername,
    });
    jitter();

    // 3. Get All Conversations
    const getConvRes = http.get(`${BASE_URL}/users/get_all_conversations/${userId}`, auth);
    check(getConvRes, { 'get_all_conversations → status 200': (r) => r.status === 200 });
    jitter();

    // 4. Change Username
    // We maintain the "Test_" prefix here so it remains fast if the user ever logs out and re-logs in
    const newUsername = `Test_vur_${randomString(8)}`;
    const changePayload = JSON.stringify({ newUsername });
    const changeRes = http.post(`${BASE_URL}/users/change_username/${userId}`, changePayload, auth);
    
    if (check(changeRes, { 'change_username → status 200': (r) => r.status === 200 })) {
        currentUsername = newUsername; 
    }

    // 5. Verify rename persisted
    const verifyRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
    check(verifyRes, { 'change_username → verify updated': (r) => r.json('username') === currentUsername });
    
    jitter();
}