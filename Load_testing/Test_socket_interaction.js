// ─── K6 Load Test — WebSocket Heavy Interaction (One-Time Setup) ────────────
import http from 'k6/http';
import ws   from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';
import exec from 'k6/execution';

// ─── Environment ─────────────────────────────────────────────────────────────
const BASE_URL = 'http://34.44.178.171:8001/ping/api';
const WS_URL   = 'ws://34.44.178.171:8001/ping/api';

// ─── Custom Metrics ──────────────────────────────────────────────────────────
const wsMsgSent     = new Counter('ws_messages_sent');
const wsMsgReceived = new Counter('ws_messages_received');
const wsRoundTrip   = new Trend('ws_round_trip_ms', true);

// ─── Stage Configuration ─────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '2m', target: 400  },
    { duration: '2m', target: 400 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_failed:          ['rate<0.05'],
    http_req_duration:        ['p(95)<3000'],
    ws_connecting:            ['p(95)<4000'],
    ws_session_duration:      ['p(95)<60000'],
    ws_messages_sent:         ['count>0'],
  },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function parseJWT(token) {
  try {
    if (!token) return null;
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    let base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) base64 += '=';
    return JSON.parse(encoding.b64decode(base64, 'std', 's'));
  } catch (e) {
    return null;
  }
}

function nowISO() { return new Date().toISOString(); }
function jitter(max) { sleep(Math.random() * (max || 5)); }

function authHeaders(token) {
  return { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` } };
}

// ─── VU State Variables ──────────────────────────────────────────────────────
let isSetupComplete = false;
let token = null;
let auth = null;
let userId = null;
let currentUsername = null;
const password = 'Loadtest@99';

// ─── Default Function ─────────────────────────────────────────────────────────
export default function () {
  const vuId = exec.vu.idInTest;

  // ─── PHASE 1: ONE-TIME SETUP (REGISTER & LOGIN) ──────────────────────────
  if (!isSetupComplete) {
    const suffix = randomString(6);
    
    // Use 'Test_' prefix to bypass CPU-heavy bcrypt operations
    currentUsername = `Test_ws_vu${vuId}_${suffix}`;

    // 1. Register
    const registerRes = http.post(
      `${BASE_URL}/register`, 
      JSON.stringify({
        username: currentUsername,
        password: password,
        name:  `WS Test ${vuId}`,
        email: `${currentUsername}@wstest.io`,
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );

    if (!check(registerRes, { 'register → status 200': (r) => r.status === 200 })) {
      console.error(`[VU ${vuId}] Register Failed | Status: ${registerRes.status} | Body: ${registerRes.body}`);
      sleep(1); 
      return; // Exit iteration early if registration fails
    }

    jitter(1);

    // 2. Login
    const loginRes = http.post(
      `${BASE_URL}/login/credentials`,
      JSON.stringify({ username: currentUsername, password: password }),
      { headers: { 'Content-Type': 'application/json' } }
    );

    if (check(loginRes, { 'login → status 200': (r) => r.status === 200 })) {
      token = loginRes.json('token');
      const payload = parseJWT(token);
      
      if (payload) {
        userId = payload.user_id;
        auth = authHeaders(token);
        isSetupComplete = true; // Setup successful, lock it in for this VU
      } else {
        console.error(`[VU ${vuId}] JWT Parse Failed | Token: ${token}`);
        sleep(1);
        return;
      }
    } else {
      console.error(`[VU ${vuId}] Login Failed | Status: ${loginRes.status} | Body: ${loginRes.body}`);
      sleep(1);
      return; // Exit iteration early if login fails
    }
    jitter(1);
  }

  // ─── PHASE 2: WEBSOCKET INTERACTION LOOP ──────────────────────────────────

  // 1. Fetch own profile before connecting (Simulating App Load)
  const profileRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
  if (!check(profileRes, { 'pre-ws get_user_info → 200': (r) => r.status === 200 })) {
    console.error(`[VU ${vuId}] Get User Info Failed | Status: ${profileRes.status} | Body: ${profileRes.body}`);
  }
  jitter(1);

  // 2. WebSocket Session
  const MAX_MESSAGES     = 10 + Math.floor(Math.random() * 11); // 10–20 msgs
  const SEND_INTERVAL_MS = 1500 + Math.random() * 2000;         // 1.5–3.5 s
  const SESSION_CAP_MS   = 45000;                               // hard 45s cap
  const sentTimestamps   = {};

  const wsRes = ws.connect(
    `${WS_URL}/ws/${userId}`,
    { headers: { Authorization: `Bearer ${token}` } },
    function (socket) {
      let messagesSent = 0;
      let intervalId;

      // ── On Open ──
      socket.on('open', () => {
        intervalId = socket.setInterval(() => {
          if (messagesSent >= MAX_MESSAGES) {
            clearInterval(intervalId);
            socket.close();
            return;
          }

          const sentAt  = nowISO();
          const msgBody = `lt-msg-${messagesSent + 1}-${randomString(8)}`;
          const payload = JSON.stringify({
            type:   'direct_message',
            fromId: userId,
            toId:   userId,          // self-loop; server persists + echoes back
            body:   msgBody,
            sentAt,
          });

          sentTimestamps[msgBody] = Date.now();
          socket.send(payload);
          wsMsgSent.add(1);
          messagesSent++;
        }, SEND_INTERVAL_MS);
      });

      // ── On Message ──
      socket.on('message', (raw) => {
        wsMsgReceived.add(1);

        check(raw, { 'ws → received non-empty message': (d) => d && d.length > 0 });

        try {
          const data = JSON.parse(raw);
          check(data, {
            'ws → message has type':   (d) => !!d.type,
            'ws → message has body':   (d) => typeof d.body === 'string',
          });

          // Measure round-trip latency
          if (sentTimestamps[data.body]) {
            wsRoundTrip.add(Date.now() - sentTimestamps[data.body]);
            delete sentTimestamps[data.body];
          }
        } catch (_) { }
      });

      // ── On Error & Close ──
      socket.on('error', (e) => {
        console.error(`[VU ${vuId}] WebSocket Error: ${e.error()}`);
        check(null, { 'ws → no socket error': () => false });
      });
      socket.on('close', () => {});

      // ── Hard session cap ──
      socket.setTimeout(() => {
        clearInterval(intervalId);
        socket.close();
      }, SESSION_CAP_MS);
    }
  );

  if (!check(wsRes, { 'ws → upgrade status 101': (r) => r && r.status === 101 })) {
    console.error(`[VU ${vuId}] WS Upgrade Failed | Status: ${wsRes ? wsRes.status : 'undefined'} | Error: ${wsRes ? wsRes.error : 'unknown'}`);
  }

  // 3. Post-session: verify conversations were stored
  jitter(2);
  const convsRes = http.get(`${BASE_URL}/users/get_all_conversations/${userId}`, auth);
  if (!check(convsRes, {
    'post-ws get_all_conversations → 200': (r) => r.status === 200,
    'post-ws get_all_conversations → messages stored': (r) => {
      try {
        const msgs = r.json('direct_messages');
        return Array.isArray(msgs) && msgs.length > 0;
      } catch (e) {
        return false;
      }
    },
  })) {
    console.error(`[VU ${vuId}] Get Conversations Failed | Status: ${convsRes.status} | Body: ${convsRes.body}`);
  }

  jitter(3);
}