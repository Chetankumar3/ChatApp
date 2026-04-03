import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble.jsx';

export default function MessageList({ messages, isGroup = false, userMap = {} }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (!messages || messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-tx-3 text-sm italic">No messages yet — say hello!</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1.5">
      {messages.map((msg, i) => {
        const senderName = isGroup
          ? (userMap[msg.fromId]?.username || userMap[msg.fromId]?.name || `User ${msg.fromId}`)
          : '';
        // Show sender label for group messages when sender changes
        const prevMsg = messages[i - 1];
        const showSender = isGroup && (!prevMsg || prevMsg.fromId !== msg.fromId);

        return (
          <MessageBubble
            key={msg.id ?? `${msg.fromId}-${msg.sentAt}-${i}`}
            msg={msg}
            showSender={showSender}
            senderName={senderName}
          />
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
