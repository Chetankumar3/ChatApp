import Avatar from '../Avatar.jsx';
import BackButton from '../BackButton.jsx';

export default function ChatHeader({ name, id, subtitle, onBack, onInfoClick, isGroup }) {
  return (
    <div className="h-14 px-4 flex items-center gap-3 border-b border-border bg-surface shrink-0">
      {/* Back (mobile) */}
      {onBack && (
        <div className="md:hidden">
          <BackButton onClick={onBack} label="" />
        </div>
      )}

      <Avatar name={name} id={id} size="sm" />

      <div className="flex-1 min-w-0">
        <p className="text-tx-1 font-semibold text-sm truncate">{name || `#${id}`}</p>
        {subtitle && <p className="text-tx-3 text-xs truncate">{subtitle}</p>}
      </div>

      {onInfoClick && (
        <button
          onClick={onInfoClick}
          title={isGroup ? 'Group info' : 'User info'}
          className="w-8 h-8 flex items-center justify-center rounded-xl text-tx-2 hover:text-tx-1 hover:bg-hover transition-all"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z" />
          </svg>
        </button>
      )}
    </div>
  );
}
