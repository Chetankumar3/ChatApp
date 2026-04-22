// ─── K6 Load Test — Data-Driven (Login Only) ──────────────────────────────
import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';
import exec from 'k6/execution';
import { SharedArray } from 'k6/data'; // 🔥 NEW: Import SharedArray

const BASE_URL = 'http://16.112.64.12.nip.io/chatapp/api';

export const options = {
    stages: [
        { duration: '3m', target: 600 },
        { duration: '3m', target: 600 },
        { duration: '3m', target: 0 },
    ],
    gracefulRampDown: '1m',
    gracefulStop: '1m',
    thresholds: {
        http_req_failed: ['rate<0.05'],
        http_req_duration: ['p(95)<3000'],
    },
};

// 🔥 LOAD TEST DATA ONCE
// SharedArray loads the file into memory only once, saving massive amounts of RAM
const testUsers = new SharedArray('users data', function () {
    return JSON.parse(open('./users.json')); 
});

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

function checkAndLog(res, checkObj, contextName) {
    const passed = check(res, checkObj);
    if (!passed) {
        const errorDetails = {
            timestamp: new Date().toISOString(),
            action: contextName,
            vuId: exec.vu.idInTest,
            iteration: exec.vu.iterationInInstance,
            request: { method: res.request.method, url: res.request.url, body: res.request.body },
            response: { status: res.status, body: res.body }
        };
        console.error(JSON.stringify(errorDetails));
    }
    return passed;
}

// ─── VU State Variables ──────────────────────────────────────────────────────
let token = null;
let auth = null;
let userId = null;
let currentUsername = null;

// ─── Default Function ────────────────────────────────────────────────────────
export default function () {
    
    // ─── PHASE 1: ONE-TIME SETUP (LOGIN ONLY) ────────────────────────────────
    if (!token) {
        const vuId = exec.vu.idInTest;
        
        // 🔥 MAP VU ID TO JSON DATA
        // VU IDs start at 1. Array indexes start at 0.
        // We use modulo (%) just in case you have more VUs than users in the JSON
        const userData = testUsers[(vuId - 1) % testUsers.length];
        
        currentUsername = userData.username; 
        const password = userData.password;

        // Login
        const loginPayload = JSON.stringify({ username: currentUsername, password });
        const loginRes = http.post(
            `${BASE_URL}/login/credentials`,
            loginPayload,
            { headers: { 'Content-Type': 'application/json' } }
        );

        if (!checkAndLog(loginRes, { 'login → status 200': (r) => r.status === 200 }, "Login API")) return;

        // Save state
        const tempToken = loginRes.json('token');
        const payload = parseJWT(tempToken);
        if (!payload) return;

        token = tempToken;
        userId = payload.user_id;
        auth = authHeaders(token);
        jitter(); // No massive sleeps needed!
    }

    // ─── PHASE 2: CONTINUOUS LOAD ────────────────────────────────────────────

    // 1. Get All Users
    const getAllRes = http.get(`${BASE_URL}/get_all_users`, auth);
    checkAndLog(getAllRes, { 'get_all_users → status 200': (r) => r.status === 200 }, "Get All Users API");
    jitter();

    // 2. Get User Info
    const getUserRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
    checkAndLog(getUserRes, { 
        'get_user_info → status 200': (r) => r.status === 200,
        'get_user_info → correct username': (r) => r.json('username') === currentUsername,
    }, "Get User Info API");
    jitter();

    // 3. Get All Conversations
    const getConvRes = http.get(`${BASE_URL}/users/get_all_conversations/${userId}`, auth);
    checkAndLog(getConvRes, { 'get_all_conversations → status 200': (r) => r.status === 200 }, "Get All Conversations API");
    jitter();

    // 4. Change Username
    // (Note: This will still scramble their names in the DB, but since we update 
    // currentUsername locally, the assertions will still pass during this test run)
    const newUsername = `vur_${randomString(10)}`;
    const changePayload = JSON.stringify({ newUsername });
    const changeRes = http.post(
        `${BASE_URL}/users/change_username/${userId}`,
        changePayload,
        auth
    );
    
    if (checkAndLog(changeRes, { 'change_username → status 200': (r) => r.status === 200 }, "Change Username API")) {
        currentUsername = newUsername; 
        // ⚠️ CRITICAL: The next time you run this test, the names in users.json 
        // will no longer match the database! 
    }

    // 5. Verify rename persisted
    const verifyRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
    checkAndLog(verifyRes, { 'change_username → verify updated': (r) => r.json('username') === currentUsername }, "Verify Rename API");
    
    jitter();
}