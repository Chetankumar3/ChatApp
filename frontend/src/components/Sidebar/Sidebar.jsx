import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { useChat } from '../../context/ChatContext.jsx';
import ConvItem from './ConvItem.jsx';
import NewFriendModal from './NewFriendModal.jsx';
import CreateGroupModal from './CreateGroupModal.jsx';
import Avatar from '../Avatar.jsx';
import Spinner from '../Spinner.jsx';

export default function Sidebar({ onSelect }) {
  const navigate = useNavigate();
  const { me, logout } = useAuth();
  const { directConvs, groupConvs, activeConv, setActiveConv, chatLoading } = useChat();

  const [query, setQuery]           = useState('');
  const [showNewFriend, setShowNewFriend] = useState(false);
  const [showNewGroup, setShowNewGroup]   = useState(false);
  const [showUserMenu, setShowUserMenu]   = useState(false);

  // Build unified sorted list by last message time
  const conversations = useMemo(() => {
    const list = [];

    Object.entries(directConvs).forEach(([id, conv]) => {
      const msgs = conv.messages;
      const last = msgs[msgs.length - 1];
      list.push({
        type:     'direct',
        id:       Number(id),
        username:  conv.user?.username,
        name:  conv.user?.name,
        lastMsg:  last?.body || '',
        lastTime: last?.sentAt || '',
        displayPictureUrl: conv.user?.displayPictureUrl,
      });
    });

    Object.entries(groupConvs).forEach(([id, conv]) => {
      const msgs = conv.messages;
      const last = msgs[msgs.length - 1];
      list.push({
        type:     'group',
        id:       Number(id),
        name:     conv.group?.name || `Group ${id}`,
        lastMsg:  last?.body || '',
        lastTime: last?.sentAt || '',
        displayPictureUrl: conv.group?.displayPictureUrl,
      });
    });

    list.sort((a, b) => {
      if (!a.lastTime && !b.lastTime) return 0;
      if (!a.lastTime) return 1;
      if (!b.lastTime) return -1;
      return new Date(b.lastTime) - new Date(a.lastTime);
    });

    console.log(list);
    return list;
  }, [directConvs, groupConvs]);

  const filtered = query.trim()
    ? conversations.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()))
    : conversations;

  const handleSelect = (conv) => {
    setActiveConv({ type: conv.type, id: conv.id });
    onSelect?.();
  };

  return (
    <aside className="h-full flex flex-col bg-surface border-r border-border">
      {/* ── Top bar ── */}
      <div className="px-4 pt-4 pb-3 border-b border-border shrink-0">
        <div className="flex items-center justify-between mb-4">
          {/* App name */}
          <span className="text-tx-1 font-semibold text-lg tracking-tight">Ping</span>

          {/* User avatar + menu */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu((v) => !v)}
              className="focus:outline-none"
            >
              <Avatar name={me?.username || me?.name} id={me?.id} src={me?.displayPictureUrl} size="sm" />
            </button>
            {showUserMenu && (
              <div className="absolute right-0 top-10 z-20 bg-elevated border border-border rounded-xl shadow-xl w-44 py-1 animate-fade-in">
                <button
                  onClick={() => { setShowUserMenu(false); navigate('/profile'); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-tx-1 hover:bg-hover transition-colors"
                >
                  Profile
                </button>
                <div className="border-t border-border my-1" />
                <button
                  onClick={() => { setShowUserMenu(false); logout(); }}
                  className="w-full text-left px-4 py-2.5 text-sm text-red-400 hover:bg-hover transition-colors"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Search bar + New Friend button */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-tx-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-hover border border-border rounded-xl pl-8 pr-3 py-2 text-xs text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent transition-colors"
            />
          </div>
          <button
            title="New Friend"
            onClick={() => setShowNewFriend(true)}
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-hover border border-border hover:border-accent hover:text-accent-h text-tx-2 transition-all shrink-0"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </button>
          <button
            title="New Group"
            onClick={() => setShowNewGroup(true)}
            className="w-9 h-9 flex items-center justify-center rounded-xl bg-hover border border-border hover:border-accent hover:text-accent-h text-tx-2 transition-all shrink-0"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* ── Conversation list ── */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {chatLoading && (
          <div className="flex justify-center pt-10"><Spinner /></div>
        )}
        {!chatLoading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <div className="w-12 h-12 rounded-2xl bg-hover flex items-center justify-center">
              <svg className="w-6 h-6 text-tx-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <p className="text-tx-3 text-xs">
              {query ? 'No results' : 'No conversations yet'}
            </p>
          </div>
        )}
        {!chatLoading && filtered.map((conv) => (
          <ConvItem
            key={`${conv.type}-${conv.id}`}
            name={conv.name}
            id={conv.id}
            src = {conv.displayPictureUrl}
            username={conv.username}
            lastMsg={conv.lastMsg}
            lastTime={conv.lastTime}
            unread={0}
            active={activeConv?.type === conv.type && activeConv?.id === conv.id}
            onClick={() => handleSelect(conv)}
            type={conv.type}
          />
        ))}
      </div>

      <NewFriendModal   open={showNewFriend} onClose={() => setShowNewFriend(false)} />
      <CreateGroupModal open={showNewGroup}  onClose={() => setShowNewGroup(false)} />
    </aside>
  );
}
