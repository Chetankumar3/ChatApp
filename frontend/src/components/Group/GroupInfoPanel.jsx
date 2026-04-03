import { useState, useEffect } from 'react';
import Avatar from '../Avatar.jsx';
import Spinner from '../Spinner.jsx';
import Modal from '../Modal.jsx';
import { getAllUsers } from '../../api/users.js';
import { getGroupInfo, updateGroup, addMembers, exitGroup, deleteGroup } from '../../api/groups.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { useChat } from '../../context/ChatContext.jsx';

export default function GroupInfoPanel({ groupId, onClose }) {
  const { userId } = useAuth();
  const { setGroupConvs, removeGroupConv } = useChat();

  const [info, setInfo]         = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');

  // Add members modal state
  const [showAddModal, setShowAddModal]   = useState(false);
  const [allUsers, setAllUsers]           = useState([]);
  const [selectedNew, setSelectedNew]     = useState(new Set());
  const [addLoading, setAddLoading]       = useState(false);
  const [addQuery, setAddQuery]           = useState('');

  // Edit state
  const [editing, setEditing]   = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [saving, setSaving]     = useState(false);

  const fetchInfo = async () => {
    setLoading(true);
    try {
      const data = await getGroupInfo(groupId);
      setInfo(data);
      // Check if current user is admin (we detect from mapTable; for now compare with group data)
      // The group info returns members as usernames; we need another approach.
      // We track admin from groupConvs context for now.
      setEditName(data.name || '');
      setEditDesc(data.description || '');
    } catch (e) {
      setError(e.message || 'Failed to load group info');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (groupId) fetchInfo();
  }, [groupId]);

  const handleSaveEdit = async () => {
    setSaving(true);
    try {
      await updateGroup(userId, groupId, { name: editName.trim(), description: editDesc.trim() });
      setGroupConvs((prev) => ({
        ...prev,
        [groupId]: { ...prev[groupId], group: { ...prev[groupId]?.group, name: editName.trim(), description: editDesc.trim() } },
      }));
      setEditing(false);
      await fetchInfo();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleExit = async () => {
    if (!window.confirm('Leave this group?')) return;
    try {
      await exitGroup(groupId, userId);
      removeGroupConv(groupId);
      onClose();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this group permanently?')) return;
    try {
      await deleteGroup(userId, groupId);
      removeGroupConv(groupId);
      onClose();
    } catch (e) {
      setError(e.message);
    }
  };

  // ── Add members
  const openAddModal = async () => {
    setSelectedNew(new Set());
    setAddQuery('');
    const d = await getAllUsers().catch(() => ({ users: [] }));
    const existingNames = new Set(info?.members || []);
    setAllUsers((d.users || []).filter((u) => !existingNames.has(u.username) && u.id !== userId));
    setShowAddModal(true);
  };

  const handleAddMembers = async () => {
    if (!selectedNew.size) return;
    setAddLoading(true);
    try {
      await addMembers(userId, groupId, [...selectedNew]);
      setShowAddModal(false);
      await fetchInfo();
    } catch (e) {
      setError(e.message);
    } finally {
      setAddLoading(false);
    }
  };

  const filteredNew = addQuery.trim()
    ? allUsers.filter((u) => (u.username || '').toLowerCase().includes(addQuery.toLowerCase()))
    : allUsers;

  return (
    <aside className="w-72 h-full border-l border-border bg-surface flex flex-col animate-slide-right shrink-0 overflow-y-auto">
      {/* Header */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-border shrink-0">
        <span className="text-tx-1 font-semibold text-sm">Group Info</span>
        <button onClick={onClose} className="w-7 h-7 flex items-center justify-center rounded-lg text-tx-2 hover:text-tx-1 hover:bg-hover transition-colors">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 px-4 py-4 space-y-5">
        {loading && <div className="flex justify-center pt-10"><Spinner /></div>}
        {error && <p className="text-red-400 text-xs">{error}</p>}

        {!loading && info && (<>
          {/* Group identity */}
          {!editing ? (
            <div className="flex flex-col items-center gap-2 text-center">
              <Avatar name={info.name} id={groupId} size="lg" />
              <p className="text-tx-1 font-semibold">{info.name}</p>
              {info.description && <p className="text-tx-2 text-xs">{info.description}</p>}
              <button
                onClick={() => setEditing(true)}
                className="text-xs text-accent-h hover:underline mt-1"
              >
                Edit group
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Group name"
                className="w-full bg-hover border border-border rounded-xl px-3 py-2 text-sm text-tx-1 outline-none focus:border-accent"
              />
              <input
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                placeholder="Description"
                className="w-full bg-hover border border-border rounded-xl px-3 py-2 text-sm text-tx-1 outline-none focus:border-accent"
              />
              <div className="flex gap-2">
                <button onClick={() => setEditing(false)} className="flex-1 py-2 text-xs text-tx-2 border border-border rounded-xl hover:bg-hover transition-colors">Cancel</button>
                <button onClick={handleSaveEdit} disabled={saving} className="flex-1 py-2 text-xs text-white bg-accent rounded-xl hover:bg-accent-h transition-colors disabled:opacity-50 flex items-center justify-center gap-1">
                  {saving ? <Spinner size="sm" /> : 'Save'}
                </button>
              </div>
            </div>
          )}

          <div className="border-t border-border" />

          {/* Members */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-tx-2 text-xs uppercase tracking-wider">Members ({(info.members || []).length})</span>
              <button
                onClick={openAddModal}
                className="text-xs text-accent-h hover:underline flex items-center gap-1"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                Add
              </button>
            </div>
            <div className="space-y-1">
              {(info.members || []).map((username) => (
                <div key={username} className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg">
                  <Avatar name={username} id={username} size="sm" />
                  <span className="text-tx-1 text-sm truncate">{username}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-border" />

          {/* Danger zone */}
          <div className="space-y-2">
            <button
              onClick={handleExit}
              className="w-full py-2.5 text-sm text-orange-400 border border-orange-400/20 rounded-xl hover:bg-orange-400/10 transition-colors"
            >
              Leave Group
            </button>
            <button
              onClick={handleDelete}
              className="w-full py-2.5 text-sm text-red-400 border border-red-400/20 rounded-xl hover:bg-red-400/10 transition-colors"
            >
              Delete Group
            </button>
          </div>
        </>)}
      </div>

      {/* Add Members Modal */}
      <Modal open={showAddModal} onClose={() => setShowAddModal(false)} title="Add Members">
        <div className="relative mb-3">
          <input
            autoFocus
            type="text"
            placeholder="Search username…"
            value={addQuery}
            onChange={(e) => setAddQuery(e.target.value)}
            className="w-full bg-hover border border-border rounded-xl px-3 py-2 text-sm text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent"
          />
        </div>
        <div className="max-h-52 overflow-y-auto space-y-0.5 mb-3">
          {filteredNew.map((u) => {
            const sel = selectedNew.has(u.id);
            return (
              <button key={u.id} onClick={() => setSelectedNew((p) => { const n = new Set(p); sel ? n.delete(u.id) : n.add(u.id); return n; })}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-left ${sel ? 'bg-accent/10 border border-accent/30' : 'hover:bg-hover border border-transparent'}`}>
                <Avatar name={u.username || '?'} id={u.id} size="sm" />
                <span className="text-tx-1 text-sm flex-1 truncate">{u.username || `User ${u.id}`}</span>
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 ${sel ? 'bg-accent border-accent' : 'border-border'}`}>
                  {sel && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
                </div>
              </button>
            );
          })}
        </div>
        <button onClick={handleAddMembers} disabled={!selectedNew.size || addLoading}
          className="w-full py-2.5 bg-accent hover:bg-accent-h disabled:opacity-50 text-white text-sm rounded-xl transition-colors flex items-center justify-center gap-2">
          {addLoading ? <Spinner size="sm" /> : `Add ${selectedNew.size || ''} member${selectedNew.size !== 1 ? 's' : ''}`}
        </button>
      </Modal>
    </aside>
  );
}
