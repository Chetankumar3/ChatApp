import { apiFetch } from './client.js';

export function getAllUsers() {
  return apiFetch('/get_all_users');
}

export function getUserInfo(userId) {
  return apiFetch(`/users/get_user_info/${userId}`);
}

export function getAllConversations(userId) {
  return apiFetch(`/users/get_all_conversations/${userId}`);
}

export function changeUsername(userId, newUsername) {
  return apiFetch(`/users/change_username/${userId}`, {
    method: 'POST',
    body: JSON.stringify({ newUsername }),
  });
}
