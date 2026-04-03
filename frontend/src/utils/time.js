export const SESSION_DURATION_MS = 2 * 60 * 60 * 1000; // 2 hours

export function isSessionValid(loginTime) {
  if (!loginTime) return false;
  return Date.now() - Number(loginTime) < SESSION_DURATION_MS;
}

export function formatMsgTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatConvTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const isThisYear = d.getFullYear() === now.getFullYear();
  if (isThisYear) return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  return d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
}

export function nowISO() {
  return new Date().toISOString();
}
