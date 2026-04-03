import Avatar from '../Avatar.jsx';
import { formatConvTime } from '../../utils/time.js';

export default function ConvItem({type, name, id, src, username, lastMsg, lastTime, unread = 0, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all text-left group ${
        active
          ? 'bg-accent/10 border border-accent/20'
          : 'hover:bg-hover border border-transparent'
      }`}
    >
      <Avatar name={name} id={id} src={src} size="md" />

      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className={`text-sm font-medium truncate ${active ? 'text-accent-h' : 'text-tx-1'}`}>
            {type === 'direct' ? username : name}
          </span>
          {lastTime && (
            <span className="text-tx-3 text-xs shrink-0">{formatConvTime(lastTime)}</span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 mt-0.5">
          <p className="text-tx-2 text-xs truncate">
            {lastMsg || <span className="text-tx-3 italic">No messages yet</span>}
          </p>
          {unread > 0 && (
            <span className="shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-accent text-white text-[10px] font-semibold flex items-center justify-center">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}
