import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import exec from 'k6/execution';

const BASE_URL = 'http://16.112.64.12.nip.io/ping/api';

export const options = {
    // 15 Minutes Total Duration
    stages: [
        { duration: '2m', target: 200 },  // Gently ramp up to 200 concurrent creators
        { duration: '11m', target: 200 }, // Hold steady for 11 minutes
        { duration: '2m', target: 0 },    // Gracefully ramp down
    ],
    thresholds: {
        http_req_failed: ['rate<0.05'],
    },
};

export default function () {
    // 1. GENERATE GUARANTEED UNIQUE IDENTITY
    // By combining VU ID, Iteration Number, and a random string, 
    // we guarantee no database unique-constraint collisions.
    const vuId = exec.vu.idInTest;
    const iter = exec.vu.iterationInInstance;
    const rand = randomString(4);
    
    const currentUsername = `vu_${vuId}_i${iter}_${rand}`;
    const password = 'Loadtest@99';

    // 2. BUILD PAYLOAD
    const payload = JSON.stringify({
        username: currentUsername,
        password: password,
        name: `Test User ${vuId}-${iter}`,
        email: `${currentUsername}@loadtest.io`,
    });

    // 3. SEND REGISTRATION
    const res = http.post(
        `${BASE_URL}/register`,
        payload,
        { headers: { 'Content-Type': 'application/json' } }
    );

    check(res, {
        'register → status 200': (r) => r.status === 200,
    });

    // 4. PACE THE GENERATION
    // Sleeping for exactly 1 second means each VU creates ~1 user per second.
    // With 200 VUs, this will generate roughly 200 users/sec -> 12,000 users/min.
    // Over 15 minutes, this will safely seed over 150,000 users into your database!
    sleep(1); 
}