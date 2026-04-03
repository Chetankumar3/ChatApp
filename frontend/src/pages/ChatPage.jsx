import { useState } from 'react';
import Sidebar from '../components/Sidebar/Sidebar.jsx';
import DirectChatView from '../components/Chat/DirectChatView.jsx';
import GroupChatView from '../components/Chat/GroupChatView.jsx';
import EmptyState from '../components/Chat/EmptyState.jsx';
import { useChat } from '../context/ChatContext.jsx';

export default function ChatPage() {
  const { activeConv } = useChat();
  // On mobile we either show sidebar or chat. Default: sidebar.
  const [mobileShowChat, setMobileShowChat] = useState(false);

  const handleConvSelect = () => setMobileShowChat(true);
  const handleBack       = () => setMobileShowChat(false);

  const renderChat = () => {
    if (!activeConv) return <EmptyState />;
    if (activeConv.type === 'direct') return <DirectChatView onBack={handleBack} />;
    if (activeConv.type === 'group')  return <GroupChatView  onBack={handleBack} />;
    return <EmptyState />;
  };

  return (
    <div className="h-full flex overflow-hidden bg-base">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      {/* Desktop: always visible. Mobile: visible when no chat open. */}
      <div className={`
        w-full md:w-80 lg:w-[22rem] shrink-0 h-full
        md:block
        ${mobileShowChat ? 'hidden' : 'block'}
      `}>
        <Sidebar onSelect={handleConvSelect} />
      </div>

      {/* ── Chat pane ─────────────────────────────────────────────────────── */}
      <div className={`
        flex-1 h-full min-w-0
        md:flex
        ${mobileShowChat ? 'flex' : 'hidden'}
        flex-col
      `}>
        {renderChat()}
      </div>
    </div>
  );
}
