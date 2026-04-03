import { useState, useEffect } from 'react';
import Modal from '../Modal.jsx';
import Avatar from '../Avatar.jsx';
import Spinner from '../Spinner.jsx';
import { getAllUsers } from '../../api/users.js';
import { createGroup } from '../../api/groups.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { useChat } from '../../context/ChatContext.jsx';

export default function CreateGroupModal({ open, onClose }) {
  const { userId } = useAuth();
  const { addGroupConv } = useChat();

  const [name, setName]           = useState('');
  const [desc, setDesc]           = useState('');
  const [allUsers, setAllUsers]   = useState([]);
  const [selected, setSelected]   = useState(new Set());
  const [query, setQuery]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState('');

  useEffect(() => {
    if (!open) return;
    setName(''); setDesc(''); setSelected(new Set()); setQuery(''); setError('');
    setLoading(true);
    getAllUsers()
      .then((d) => setAllUsers((d.users || []).filter((u) => u.id !== userId)))
      .catch(() => setError('Failed to load users'))
      .finally(() => setLoading(false));
  }, [open, userId]);

  const toggleUser = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const filtered = query.trim()
    ? allUsers.filter((u) => (u.username || '').toLowerCase().includes(query.toLowerCase()))
    : allUsers;

  const handleCreate = async () => {
    if (!name.trim()) { setError('Group name is required'); return; }
    setSaving(true);
    setError('');
    try {
      console.log(selected);
      const result = await createGroup(
        { name: name.trim(), description: desc.trim() || undefined, members: Array.from(selected)},
        userId
      );
      addGroupConv({ id: result.groupId ?? result.group_id, name: name.trim(), description: desc.trim() });
      onClose();
    } catch (e) {
      setError(e.message || 'Failed to create group');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="New Group" width="max-w-lg">
      <div className="space-y-3">
        <input
          autoFocus
          type="text"
          placeholder="Group name *"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={30}
          className="w-full bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent transition-colors"
        />
        <input
          type="text"
          placeholder="Description (optional)"
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          maxLength={100}
          className="w-full bg-hover border border-border rounded-xl px-4 py-2.5 text-sm text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent transition-colors"
        />

        <div>
          <p className="text-tx-2 text-xs mb-2">
            Add members
            {selected.size > 0 && (
              <span className="ml-2 bg-accent/20 text-accent-h text-xs px-1.5 py-0.5 rounded-md">
                {selected.size} selected
              </span>
            )}
          </p>
          <div className="relative mb-2">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-tx-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search username…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-hover border border-border rounded-xl pl-8 pr-3 py-2 text-xs text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent transition-colors"
            />
          </div>

          <div className="max-h-52 overflow-y-auto space-y-0.5">
            {loading && <div className="flex justify-center py-6"><Spinner /></div>}
            {!loading && filtered.length === 0 && (
              <p className="text-tx-3 text-xs text-center py-4">No users found</p>
            )}
            {!loading && filtered.map((u) => {
              const isSel = selected.has(u.id);
              return (
                <button
                  key={u.id}
                  onClick={() => toggleUser(u.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-left ${
                    isSel ? 'bg-accent/10 border border-accent/30' : 'hover:bg-hover border border-transparent'
                  }`}
                >
                  <Avatar name={u.username || '?'} src={u.displayPictureUrl} id={u.id} size="sm" />
                  <span className="text-tx-1 text-sm truncate flex-1">{u.username || `User ${u.id}`}</span>
                  <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all ${
                    isSel ? 'bg-accent border-accent' : 'border-border'
                  }`}>
                    {isSel && (
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {error && <p className="text-red-400 text-xs">{error}</p>}

        <div className="flex gap-2 pt-1">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-border text-tx-2 hover:text-tx-1 hover:border-tx-3 text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={saving || !name.trim()}
            className="flex-1 py-2.5 rounded-xl bg-accent hover:bg-accent-h disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            {saving ? <Spinner size="sm" /> : 'Create Group'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
