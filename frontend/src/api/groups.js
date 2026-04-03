import { apiFetch } from './client.js';

// members: number[]  →  sent as repeated query params (?members=1&members=2)
export function createGroup(groupBody, creatorId) {
  return apiFetch(`/groups/create/${creatorId}`, {
    method: 'PUT',
    body: JSON.stringify(groupBody),
  });
}

export function getGroupInfo(groupId) {
  return apiFetch(`/groups/get_group_info/${groupId}`);
}

export function updateGroup(modifierId, groupId, groupBody) {
  return apiFetch(`/groups/update/${modifierId}/${groupId}`, {
    method: 'PUT',
    body: JSON.stringify(groupBody),
  });
}

export function addMembers(modifierId, groupId, userIds) {
  return apiFetch(`/groups/add_member/${modifierId}/${groupId}`, {
    method: 'POST',
    body: JSON.stringify(userIds),
  });
}

export function exitGroup(groupId, userId) {
  return apiFetch(`/groups/exit/${groupId}/${userId}`, { method: 'DELETE' });
}

export function deleteGroup(modifierId, groupId) {
  return apiFetch(`/groups/delete/${modifierId}/${groupId}`, { method: 'DELETE' });
}
