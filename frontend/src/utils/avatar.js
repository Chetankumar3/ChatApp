const COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899',
  '#f59e0b', '#10b981', '#3b82f6',
  '#ef4444', '#14b8a6', '#f97316',
];

export function avatarColor(id) {
  return COLORS[Math.abs(Number(id) || 0) % COLORS.length];
}

export function initials(name) {
  if (!name) return '?';
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}
