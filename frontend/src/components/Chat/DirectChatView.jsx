import { useChat } from '../../context/ChatContext.jsx';
import ChatHeader from './ChatHeader.jsx';
import MessageList from './MessageList.jsx';
import MessageInput from './MessageInput.jsx';

export default function DirectChatView({ onBack }) {
  const { activeConv, directConvs, sendMessage } = useChat();
  if (!activeConv || activeConv.type !== 'direct') return null;

  const conv = directConvs[activeConv.id];
  const user = conv?.user;
  const messages = conv?.messages || [];

  const name = user?.username || user?.name || `User ${activeConv.id}`;

  const handleSend = (body) => {
    sendMessage('direct', activeConv.id, body);
  };

  return (
    <div className="flex flex-col h-full">
      <ChatHeader
        name={name}
        id={activeConv.id}
        subtitle={user?.email}
        onBack={onBack}
        isGroup={false}
      />
      <MessageList messages={messages} isGroup={false} />
      <MessageInput onSend={handleSend} />
    </div>
  );
}
