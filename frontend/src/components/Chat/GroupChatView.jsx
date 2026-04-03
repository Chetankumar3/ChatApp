import { useState, useMemo } from 'react';
import { useChat } from '../../context/ChatContext.jsx';
import ChatHeader from './ChatHeader.jsx';
import MessageList from './MessageList.jsx';
import MessageInput from './MessageInput.jsx';
import GroupInfoPanel from '../Group/GroupInfoPanel.jsx';

export default function GroupChatView({ onBack }) {
  const { activeConv, groupConvs, sendMessage } = useChat();
  const [showInfo, setShowInfo] = useState(false);

  const conv     = activeConv?.type === 'group' ? groupConvs[activeConv.id] : null;
  const group    = conv?.group;
  const messages = conv?.messages || [];

  // Build userMap from sender ids present in messages (best-effort; no extra API call)
  const userMap = useMemo(() => {
    const map = {};
    messages.forEach((m) => {
      if (!map[m.fromId]) map[m.fromId] = { id: m.fromId };
    });
    return map;
  }, [messages]); // safe: messages is stable reference from context state

  // Early return AFTER all hooks
  if (!activeConv || activeConv.type !== 'group') return null;

  const name = group?.name || `Group ${activeConv.id}`;

  const handleSend = (body) => {
    sendMessage('group', activeConv.id, body);
  };

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex flex-col flex-1 min-w-0 h-full">
        <ChatHeader
          name={name}
          id={activeConv.id}
          subtitle={group?.description}
          onBack={onBack}
          isGroup
          onInfoClick={() => setShowInfo((v) => !v)}
        />
        <MessageList messages={messages} isGroup userMap={userMap} />
        <MessageInput onSend={handleSend} />
      </div>

      {showInfo && (
        <GroupInfoPanel
          groupId={activeConv.id}
          onClose={() => setShowInfo(false)}
        />
      )}
    </div>
  );
}
