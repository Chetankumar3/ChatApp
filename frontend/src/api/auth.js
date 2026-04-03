import { apiFetch } from './client.js';

// Sends Google ID token to backend, receives { userId }
export function loginWithGoogle(idToken) {
  return apiFetch('/login', {
    method: 'POST',
    body: JSON.stringify({ token: idToken }),
  });
}
