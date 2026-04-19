// ─── K6 Load Test — WebSocket Heavy Interaction ─────────────────────────────
// Flow: Register → Login → Open WS → Loop 10-20 direct messages → Close
// Ramp: 0 → 1000 VUs over 1m │ Hold 1m │ Ramp down 1m

import http from 'k6/http';
import ws   from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import encoding from 'k6/encoding';


// ─── Environment ─────────────────────────────────────────────────────────────
const BASE_URL = 'http://16.112.64.12/chatapp/api';
const WS_URL   = 'ws://16.112.64.12.nip.io/chatapp/api';

// ─── Custom Metrics ──────────────────────────────────────────────────────────
const wsMsgSent     = new Counter('ws_messages_sent');
const wsMsgReceived = new Counter('ws_messages_received');
const wsRoundTrip   = new Trend('ws_round_trip_ms', true);

// ─── Stage Configuration ─────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '1m', target: 1000 },
    { duration: '1m', target: 1000 },
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

    let base64 = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    while (base64.length % 4) base64 += '=';

    const decoded = encoding.b64decode(base64, 'std', 's');
    return JSON.parse(decoded);

  } catch (e) {
    console.error('JWT parse error:', e.message);
    return null;
  }
}

function nowISO() {
  return new Date().toISOString();
}

function jitter(max) {
  sleep(Math.random() * (max || 5));
}

function authHeaders(token) {
  return {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  };
}

// ─── Default Function ─────────────────────────────────────────────────────────
export default function () {
  const suffix   = randomString(12);
  const username = `ws_${suffix}`;
  const password = 'Loadtest@99';

  // ── Register ─────────────────────────────────────────────────────────────
  const registerRes = http.post(
    `${BASE_URL}/recruiter/register`,
    JSON.stringify({
      username,
      password,
      name:  `WS ${suffix}`,
      email: `${suffix}@wstest.io`,
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
  ) return;

  jitter(2);

  // ── Login ─────────────────────────────────────────────────────────────────
  const loginRes = http.post(
    `${BASE_URL}/login/credentials`,
    JSON.stringify({ username, password }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  if (
    !check(loginRes, {
      'login → status 200': (r) => r.status === 200,
      'login → has token':  (r) => !!r.json('token'),
    })
  ) return;

  const token   = loginRes.json('token');
  const payload = parseJWT(token);
  if (!payload) return;

  const userId = payload.user_id;
  const auth   = authHeaders(token);

  jitter(2);

  // ── Fetch own profile before connecting ───────────────────────────────────
  const profileRes = http.get(`${BASE_URL}/users/get_user_info/${userId}`, auth);
  check(profileRes, {
    'pre-ws get_user_info → 200': (r) => r.status === 200,
  });

  jitter(1);

  // ── WebSocket Session ────────────────────────────────────────────────────
  const MAX_MESSAGES     = 10 + Math.floor(Math.random() * 11); // 10–20 msgs
  const SEND_INTERVAL_MS = 1500 + Math.random() * 2000;         // 1.5–3.5 s
  const SESSION_CAP_MS   = 45000;                                // hard 45s cap

  const sentTimestamps = {};

  const wsRes = ws.connect(
    `${WS_URL}/ws/${userId}`,
    { headers: { Authorization: `Bearer ${token}` } },
    function (socket) {
      let messagesSent = 0;
      let intervalId;

      // ── On Open ────────────────────────────────────────────────────────
      socket.on('open', () => {
        intervalId = socket.setInterval(() => {
          if (messagesSent >= MAX_MESSAGES) {
            socket.clearInterval(intervalId);
            socket.close();
            return;
          }

          const sentAt  = nowISO();
          const msgBody = `lt-msg-${messagesSent + 1}-${randomString(16)}`;
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

      // ── On Message ─────────────────────────────────────────────────────
      socket.on('message', (raw) => {
        wsMsgReceived.add(1);

        check(raw, {
          'ws → received non-empty message': (d) => d && d.length > 0,
        });

        try {
          const data = JSON.parse(raw);

          check(data, {
            'ws → message has type':   (d) => !!d.type,
            'ws → message has fromId': (d) => typeof d.fromId === 'number',
            'ws → message has body':   (d) => typeof d.body === 'string',
          });

          // Measure round-trip for self-messages we sent
          if (sentTimestamps[data.body]) {
            wsRoundTrip.add(Date.now() - sentTimestamps[data.body]);
            delete sentTimestamps[data.body];
          }
        } catch (_) {
          // ignore non-JSON frames
        }
      });

      // ── On Error ───────────────────────────────────────────────────────
      socket.on('error', (e) => {
        check(null, { 'ws → no socket error': () => false });
      });

      // ── On Close ───────────────────────────────────────────────────────
      socket.on('close', () => {});

      // ── Hard session cap ───────────────────────────────────────────────
      socket.setTimeout(() => {
        socket.clearInterval(intervalId);
        socket.close();
      }, SESSION_CAP_MS);
    }
  );

  check(wsRes, {
    'ws → upgrade status 101': (r) => r && r.status === 101,
  });

  // ── Post-session: verify conversations were stored ────────────────────────
  jitter(2);

  const convsRes = http.get(
    `${BASE_URL}/users/get_all_conversations/${userId}`,
    auth
  );
  check(convsRes, {
    'post-ws get_all_conversations → 200':              (r) => r.status === 200,
    'post-ws get_all_conversations → messages stored':  (r) => {
      const msgs = r.json('direct_messages');
      return Array.isArray(msgs) && msgs.length > 0;
    },
  });

  jitter(3);
}