import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { changeUsername } from '../api/users.js';
import Avatar from '../components/Avatar.jsx';
import BackButton from '../components/BackButton.jsx';
import Spinner from '../components/Spinner.jsx';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { userId, me, refreshMe, logout } = useAuth();

  const [newUsername, setNewUsername] = useState('');
  const [saving, setSaving]           = useState(false);
  const [success, setSuccess]         = useState('');
  const [error, setError]             = useState('');

  const handleSave = async () => {
    const trimmed = newUsername.trim();
    if (!trimmed) { setError('Username cannot be empty'); return; }
    if (trimmed.length > 20) { setError('Max 20 characters'); return; }

    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await changeUsername(userId, trimmed);
      await refreshMe();
      setSuccess('Username updated!');
      setNewUsername('');
    } catch (e) {
      setError(e.message || 'Failed to update username');
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSave();
  };

  return (
    <div className="h-full bg-base flex flex-col">
      {/* Top bar */}
      <div className="h-14 px-6 flex items-center gap-4 border-b border-border bg-surface shrink-0">
        <BackButton onClick={() => navigate('/chat')} />
        <span className="text-tx-1 font-semibold text-sm">Profile</span>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col items-center py-12 px-4">
        <div className="w-full max-w-md space-y-6">

          {/* Avatar + identity */}
          <div className="flex flex-col items-center gap-3">
            <Avatar
              name={me?.username || me?.name}
              id={me?.id}
              src={me?.displayPictureUrl}
              size="lg"
            />
            <div className="text-center">
              <p className="text-tx-1 font-semibold text-lg">{me?.name || '—'}</p>
              <p className="text-tx-2 text-sm">@{me?.username || 'no username set'}</p>
              {me?.email && <p className="text-tx-3 text-xs mt-0.5">{me.email}</p>}
            </div>
          </div>

          {/* Change username card */}
          <div className="bg-surface border border-border rounded-2xl p-5 space-y-4">
            <div>
              <p className="text-tx-1 text-sm font-semibold">Change Username</p>
              <p className="text-tx-3 text-xs mt-0.5">Usernames are visible to others when searching.</p>
            </div>

            <div className="space-y-2">
              <label className="text-tx-2 text-xs">New Username</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. coolcat99"
                  value={newUsername}
                  onChange={(e) => { setNewUsername(e.target.value); setError(''); setSuccess(''); }}
                  onKeyDown={handleKeyDown}
                  maxLength={20}
                  className="flex-1 bg-hover border border-border rounded-xl px-3 py-2.5 text-sm text-tx-1 placeholder:text-tx-3 outline-none focus:border-accent transition-colors"
                />
                <button
                  onClick={handleSave}
                  disabled={saving || !newUsername.trim()}
                  className="px-4 py-2.5 bg-accent hover:bg-accent-h disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2 shrink-0"
                >
                  {saving ? <Spinner size="sm" /> : 'Save'}
                </button>
              </div>

              {error && (
                <p className="text-red-400 text-xs flex items-center gap-1.5">
                  <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                  </svg>
                  {error}
                </p>
              )}
              {success && (
                <p className="text-emerald-400 text-xs flex items-center gap-1.5">
                  <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {success}
                </p>
              )}
            </div>
          </div>

          {/* Account info card */}
          <div className="bg-surface border border-border rounded-2xl p-5 space-y-3">
            <p className="text-tx-1 text-sm font-semibold">Account Info</p>
            <div className="space-y-2">
              {[
                { label: 'User ID',       value: me?.id },
                { label: 'Mobile',        value: me?.mobileNumber || '—' },
                { label: 'Email',         value: me?.email || '—' },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center py-1.5 border-b border-border last:border-0">
                  <span className="text-tx-3 text-xs">{label}</span>
                  <span className="text-tx-2 text-xs font-medium">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sign out */}
          <button
            onClick={logout}
            className="w-full py-3 rounded-xl border border-red-400/20 text-red-400 hover:bg-red-400/10 text-sm transition-colors"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
