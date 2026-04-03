import { avatarColor, initials } from '../utils/avatar.js';

export default function Avatar({ name, id, src, size = 'md', className = '' }) {
  const sz = { sm: 'w-8 h-8 text-xs', md: 'w-10 h-10 text-sm', lg: 'w-14 h-14 text-lg' }[size];
  const bg = avatarColor(id ?? name ?? '?');

  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className={`${sz} rounded-full object-cover shrink-0 ${className}`}
      />
    );
  }
  return (
    <div
      className={`${sz} rounded-full flex items-center justify-center font-semibold shrink-0 ${className}`}
      style={{ backgroundColor: bg + '33', color: bg, border: `1.5px solid ${bg}55` }}
    >
      {initials(name)}
    </div>
  );
}
