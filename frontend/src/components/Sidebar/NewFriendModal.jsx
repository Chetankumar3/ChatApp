import { useState, useEffect } from 'react';
import Modal from '../Modal.jsx';
import Avatar from '../Avatar.jsx';
import Spinner from '../Spinner.jsx';
import { getAllUsers, getUserInfo } from '../../api/users.js';
import { useChat } from '../../context/ChatContext.jsx';

export default function NewFriendModal({ open, onClose }) {
  const { openDirectConv } = useChat();
  const [users, setUsers]   = useState([]);
  const [query, setQuery]   = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setError('');
    setLoading(true);
    getAllUsers()
      .then((data) => setUsers(data.users || []))
      .catch(() => setError('Failed to load users'))
      .finally(() => setLoading(false));
  }, [open]);

  const filtered = query.trim()
    ? users.filter((u) =>
        (u.username || '').toLowerCase().includes(query.toLowerCase())
      )
    : users;

  const handleSelect = async (u) => {
    try {
      const full = await getUserInfo(u.id).catch(() => u);
      openDirectConv(full);
      onClose();
    } catch {
      openDirectConv(u);
      onClose();
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Find People">
      <p className="text-tx-2 text-xs mb-3">Search by username to start a conversation.</p>
      <div className="relative mb-3">
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-tx-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          autoFocus
          type="text"
          placeholder="Search username…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-hover border border-border rounded-xl pl-9 pr-3 py-2.5 text-sm text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent transition-colors"
        />
      </div>

      <div className="max-h-72 overflow-y-auto -mx-1 px-1 space-y-0.5">
        {loading && (
          <div className="flex justify-center py-8"><Spinner /></div>
        )}
        {error && <p className="text-red-400 text-xs text-center py-4">{error}</p>}
        {!loading && !error && filtered.length === 0 && (
          <p className="text-tx-3 text-xs text-center py-6">No users found</p>
        )}
        {!loading && filtered.map((u) => (
          <button
            key={u.id}
            onClick={() => handleSelect(u)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-hover transition-colors text-left group"
          >
            <Avatar name={u.username || u.name || '?'} src={u.displayPictureUrl} id={u.id} size="sm" />
            <div className="min-w-0">
              <p className="text-tx-1 text-sm font-medium truncate group-hover:text-accent-h transition-colors">
                {u.username || '(no username)'}
              </p>
            </div>
            <svg className="w-4 h-4 text-tx-3 ml-auto group-hover:text-accent-h transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        ))}
      </div>
    </Modal>
  );
}
