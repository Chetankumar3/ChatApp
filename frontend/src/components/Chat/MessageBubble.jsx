import { useAuth } from '../../context/AuthContext.jsx';
import { formatMsgTime } from '../../utils/time.js';

export default function MessageBubble({ msg, showSender = false, senderName = '' }) {
  const { userId } = useAuth();
  const isMine = msg.fromId === userId;

  return (
    <div className={`flex flex-col ${isMine ? 'items-end' : 'items-start'} animate-fade-in`}>
      {showSender && !isMine && senderName && (
        <span className="text-[10px] text-accent-h ml-3 mb-0.5 font-medium">{senderName}</span>
      )}
      <div
        className={`max-w-[72%] px-3.5 py-2 rounded-2xl text-sm leading-relaxed ${
          isMine
            ? 'bg-sent text-tx-1 rounded-br-sm'
            : 'bg-recv border border-border text-tx-1 rounded-bl-sm'
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{msg.body}</p>
        <p className={`text-[10px] mt-1 text-right ${isMine ? 'text-indigo-300/60' : 'text-tx-3'}`}>
          {formatMsgTime(msg.sentAt)}
        </p>
      </div>
    </div>
  );
}
