import { apiFetch } from './client.js';

// Sends Google ID token to backend, receives { token, isNewUser }
export function loginWithGoogle(idToken) {
  return apiFetch('/login/google', {
    method: 'POST',
    body: JSON.stringify({ token: idToken }),
  });
}

// Login with username/password
export function loginWithCredentials(username, password) {
  return apiFetch('/login/credentials', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export function registerUser(username, password, name, email) {
  return apiFetch('/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, name, email }),
  });
}
