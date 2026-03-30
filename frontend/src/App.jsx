// ─── Config ──────────────────────────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_API_URL;
const WS_BASE         = import.meta.env.VITE_WS_URL;
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// ─── Imports ─────────────────────────────────────────────────────────────────
import { useState, useEffect, useRef, useCallback } from "react";

// ─── Helpers ─────────────────────────────────────────────────────────────────
const fmt = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay)
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
};

const api = async (path, opts = {}) => {
  const r = await fetch(`${API_BASE}${path}`, opts);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

// ─── Google Identity loader ───────────────────────────────────────────────────
const useGoogleGIS = () => {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (window.google?.accounts) { setReady(true); return; }
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = () => setReady(true);
    document.head.appendChild(s);
  }, []);
  return ready;
};

// ─────────────────────────────────────────────────────────────────────────────
// LOGIN SCREEN
// ─────────────────────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }) {
  const gisReady = useGoogleGIS();
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCredential = useCallback(async (response) => {
    setLoading(true);
    setErr(null);
    try {
      const data = await api(`/login`, {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: response.credential })
      });
      onLogin(data.userId);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }, [onLogin]);

  const triggerGoogle = () => {
    if (!gisReady) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredential,
    });
    window.google.accounts.id.prompt();
  };

  return (
    <div className="min-h-screen bg-[#f0ede8] flex items-center justify-center font-mono">
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap');
        * { font-family: 'IBM Plex Mono', monospace; }`}
      </style>
      <div className="bg-white border border-[#d4cfc9] w-full max-w-sm p-10 shadow-sm">
        <div className="mb-8">
          <div className="text-xs tracking-[0.2em] text-[#999] uppercase mb-1">messaging</div>
          <h1 className="text-2xl font-semibold text-[#1a1a1a] tracking-tight">Welcome back.</h1>
        </div>

        {err && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-xs">
            {err}
          </div>
        )}

        <div className="space-y-2">
          <button
            onClick={triggerGoogle}
            disabled={!gisReady || loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1a1a1a] text-white text-sm hover:bg-[#333] disabled:opacity-40 transition-colors"
          >
            <GoogleIcon />
            {loading ? "Signing in…" : "Sign in with Google"}
          </button>

          <button
            onClick={triggerGoogle}
            disabled={!gisReady || loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-[#d4cfc9] text-[#1a1a1a] text-sm hover:bg-[#f7f4f0] disabled:opacity-40 transition-colors"
          >
            <GoogleIcon dark />
            {loading ? "Signing up…" : "Sign up with Google"}
          </button>
        </div>

        <p className="mt-6 text-[10px] text-[#bbb] text-center leading-relaxed">
          Both options use the same Google authentication flow.<br />
          New accounts are created automatically on first sign-in.
        </p>
      </div>
    </div>
  );
}

function GoogleIcon({ dark }) {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill={dark ? "#4285F4" : "#ffffff"} />
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill={dark ? "#34A853" : "#ffffff"} />
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill={dark ? "#FBBC05" : "#ffffff"} />
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill={dark ? "#EA4335" : "#ffffff"} />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SET USERNAME (shown when user has no username yet)
// ─────────────────────────────────────────────────────────────────────────────
function SetUsernameScreen({ userId, onDone }) {
  const [val, setVal] = useState("");
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    const clean = val.trim();
    if (!clean) return;
    setLoading(true);
    setErr(null);
    try {
      await api(`/users/${userId}/change_username?newUsername=${encodeURIComponent(clean)}`, {
        method: "POST",
      });
      onDone(clean);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f0ede8] flex items-center justify-center font-mono">
      <div className="bg-white border border-[#d4cfc9] w-full max-w-sm p-10 shadow-sm">
        <div className="mb-6">
          <div className="text-xs tracking-[0.2em] text-[#999] uppercase mb-1">setup</div>
          <h1 className="text-xl font-semibold text-[#1a1a1a]">Choose a username</h1>
          <p className="text-xs text-[#999] mt-1">You'll use this to connect. Max 20 characters.</p>
        </div>
        {err && <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-600 text-xs">{err}</div>}
        <input
          className="w-full border border-[#d4cfc9] px-3 py-2 text-sm bg-[#faf9f7] focus:outline-none focus:border-[#1a1a1a] mb-3"
          placeholder="e.g. john_doe"
          value={val}
          maxLength={20}
          onChange={e => setVal(e.target.value)}
          onKeyDown={e => e.key === "Enter" && submit()}
        />
        <button
          onClick={submit}
          disabled={!val.trim() || loading}
          className="w-full px-4 py-2.5 bg-[#1a1a1a] text-white text-sm hover:bg-[#333] disabled:opacity-40 transition-colors"
        >
          {loading ? "Saving…" : "Continue"}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SETTINGS PANEL
// ─────────────────────────────────────────────────────────────────────────────
function SettingsPanel({ user, onUsernameChange, onClose }) {
  const [val, setVal] = useState(user.username ?? "");
  const [err, setErr] = useState(null);
  const [ok, setOk] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    const clean = val.trim();
    if (!clean || clean === user.username) return;
    setLoading(true); setErr(null); setOk(false);
    try {
      await api(`/users/${user.id}/change_username?newUsername=${encodeURIComponent(clean)}`, {
        method: "POST",
      });
      setOk(true);
      // Note: username change = websocket re-establish (handled by parent)
      onUsernameChange(clean);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-6">
      <div className="flex items-center justify-between mb-6">
        <span className="text-xs tracking-[0.15em] uppercase text-[#999]">Settings</span>
        <button onClick={onClose} className="text-[#999] hover:text-[#1a1a1a] text-xs">✕ close</button>
      </div>

      <div className="mb-6">
        <label className="block text-xs text-[#999] mb-1 uppercase tracking-wide">User ID</label>
        <div className="text-sm text-[#555] bg-[#f7f5f2] border border-[#e8e4df] px-3 py-2">{user.id}</div>
      </div>

      <div className="mb-4">
        <label className="block text-xs text-[#999] mb-1 uppercase tracking-wide">Username</label>
        <input
          className="w-full border border-[#d4cfc9] px-3 py-2 text-sm bg-white focus:outline-none focus:border-[#1a1a1a]"
          value={val}
          maxLength={20}
          onChange={e => { setVal(e.target.value); setOk(false); setErr(null); }}
          onKeyDown={e => e.key === "Enter" && submit()}
        />
      </div>

      {err && <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-600 text-xs">{err}</div>}
      {ok  && <div className="mb-3 p-2 bg-green-50 border border-green-200 text-green-700 text-xs">Username updated. WebSocket reconnected.</div>}

      <button
        onClick={submit}
        disabled={!val.trim() || val.trim() === user.username || loading}
        className="px-4 py-2 bg-[#1a1a1a] text-white text-sm hover:bg-[#333] disabled:opacity-40 transition-colors"
      >
        {loading ? "Saving…" : "Save username"}
      </button>

      <p className="mt-3 text-[10px] text-[#bbb] leading-relaxed">
        Changing your username will close and reopen your WebSocket connection.
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CHAT PANEL
// ─────────────────────────────────────────────────────────────────────────────
function ChatPanel({ user, selected, messages, ws }) {
  const [text, setText] = useState("");
  const bottomRef = useRef(null);

  const filtered = messages.filter(m => {
    if (selected.type === "personal")
      return (m.fromId === user.id && m.toId === selected.id) ||
             (m.fromId === selected.id && m.toId === user.id);
    return m.toId === selected.id; // group
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [filtered.length]);

  const send = () => {
    const clean = text.trim();
    if (!clean || !ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    const payload = {
      type: selected.type === "personal" ? 0 : 1,
      fromId: user.id,
      toId: selected.id,
      body: clean,
      sentAt: new Date().toISOString(),
    };
    ws.current.send(JSON.stringify(payload));
    setText("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-3 border-b border-[#e8e4df] bg-white flex items-center gap-2 shrink-0">
        <span className="text-sm font-medium text-[#1a1a1a]">{selected.name}</span>
        <span className="text-[10px] text-[#bbb] border border-[#e8e4df] px-1.5 py-0.5">
          {selected.type === "group" ? "group" : "direct"}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 bg-[#faf9f7]">
        {filtered.length === 0 && (
          <div className="text-xs text-[#ccc] text-center pt-10">No messages yet.</div>
        )}
        {filtered.map((m, i) => {
          const mine = m.fromId === user.id;
          return (
            <div key={m.id ?? i} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[68%] text-sm px-3 py-2 ${
                mine
                  ? "bg-[#1a1a1a] text-white"
                  : "bg-white border border-[#e8e4df] text-[#1a1a1a]"
              }`}>
                {selected.type === "group" && !mine && (
                  <div className="text-[10px] text-[#aaa] mb-1">uid:{m.fromId}</div>
                )}
                <div className="leading-relaxed">{m.body}</div>
                <div className={`text-[10px] mt-1 ${mine ? "text-[#888]" : "text-[#bbb]"} text-right`}>
                  {fmt(m.sentAt)}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-[#e8e4df] bg-white flex gap-2 shrink-0">
        <input
          className="flex-1 border border-[#d4cfc9] px-3 py-2 text-sm bg-[#faf9f7] focus:outline-none focus:border-[#1a1a1a]"
          placeholder="Message…"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
        />
        <button
          onClick={send}
          disabled={!text.trim()}
          className="px-4 py-2 bg-[#1a1a1a] text-white text-sm hover:bg-[#333] disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN APP  (sidebar + chat)
// ─────────────────────────────────────────────────────────────────────────────
function MainApp({ user, onUsernameChange }) {
  const [contacts, setContacts]   = useState([]);  // { Id, Username }
  const [groups,   setGroups]     = useState([]);  // placeholder — extend when group API lands
  const [messages, setMessages]   = useState([]);  // all Message + GroupMessage
  const [selected, setSelected]   = useState(null); // { id, type, name }
  const [wsStatus, setWsStatus]   = useState("connecting");
  const [view,     setView]       = useState("chat"); // "chat" | "settings"
  const ws = useRef(null);

  // ── Fetch contacts + history ────────────────────────────────────────────────
  useEffect(() => {
    api("/get_all_users")
      .then(d => setContacts((d.users ?? []).filter(u => u.id !== user.id)))
      .catch(console.error);

    api(`/users/${user.id}/get_all_messages`)
      .then(d => {
        const personal = (d.messages ?? []).map(m => ({ ...m, type: "personal" }));
        const grpMsgs = (d.groupMessages ?? []).map(m => ({ ...m, type: "group" }));
        setMessages([...personal, ...grpMsgs]);
      })
      .catch(console.error);
  }, [user.id]);

  // ── WebSocket ────────────────────────────────────────────────────────────────
  const connectWs = useCallback((username) => {
    if (ws.current) ws.current.close();
    const socket = new WebSocket(`${WS_BASE}/ws/${username}`);
    socket.onopen  = () => setWsStatus("online");
    socket.onerror = () => setWsStatus("error");
    socket.onclose = () => setWsStatus("offline");
    socket.onmessage = (e) => {
      try {
        const m = JSON.parse(e.data);
        setMessages(prev => [...prev, m]);
      } catch {}
    };
    ws.current = socket;
  }, []);

  useEffect(() => {
    if (user.username) connectWs(user.username);
    return () => ws.current?.close();
  }, [user.username, connectWs]);

  // username change re-establishes WS
  const handleUsernameChange = (newUsername) => {
    onUsernameChange(newUsername);      // bubble up to update user state
    connectWs(newUsername);             // reconnect
  };

  // ── Sidebar contact item ────────────────────────────────────────────────────
  const SidebarItem = ({ id, name, type }) => {
    const isActive = selected?.id === id && selected?.type === type;
    const unread = messages.filter(m =>
      type === "personal"
        ? (m.fromId === id && m.toId === user.id)
        : (m.toId === id)
    ).length;

    return (
      <button
        onClick={() => { setSelected({ id, name, type }); setView("chat"); }}
        className={`w-full text-left px-4 py-2.5 flex items-center gap-3 transition-colors ${
          isActive ? "bg-[#1a1a1a] text-white" : "text-[#ccc] hover:bg-[#2a2a2a]"
        }`}
      >
        <div className={`w-7 h-7 shrink-0 flex items-center justify-center text-[10px] font-semibold ${
          isActive ? "bg-white text-[#1a1a1a]" : "bg-[#333] text-[#bbb]"
        }`}>
          {name?.[0]?.toUpperCase() ?? "?"}
        </div>
        <span className="text-sm truncate flex-1">{name ?? `uid:${id}`}</span>
        {unread > 0 && !isActive && (
          <span className="text-[10px] bg-white text-[#1a1a1a] px-1.5 py-0.5 min-w-[18px] text-center">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>
    );
  };

  const statusColor = { online: "bg-green-400", connecting: "bg-yellow-400", offline: "bg-[#555]", error: "bg-red-400" };

  return (
    <div className="flex h-screen bg-[#f0ede8] font-mono overflow-hidden">
      {/* ── Sidebar ── */}
      <div className="w-64 shrink-0 bg-[#111] flex flex-col">
        {/* Identity bar */}
        <div className="px-4 pt-4 pb-3 border-b border-[#222]">
          <div className="flex items-center justify-between">
            <div className="truncate">
              <div className="text-[10px] text-[#555] uppercase tracking-wider">logged in as</div>
              <div className="text-sm text-white font-medium truncate">{user.username ?? `uid:${user.id}`}</div>
            </div>
            <button
              onClick={() => setView(view === "settings" ? "chat" : "settings")}
              title="Settings"
              className={`p-1.5 text-[#555] hover:text-white transition-colors ${view === "settings" ? "text-white" : ""}`}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
            </button>
          </div>
          <div className="flex items-center gap-1.5 mt-2">
            <span className={`w-1.5 h-1.5 rounded-full ${statusColor[wsStatus]}`} />
            <span className="text-[10px] text-[#555]">{wsStatus}</span>
          </div>
        </div>

        {/* Contacts */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-4 pt-4 pb-1 text-[10px] text-[#444] uppercase tracking-widest">Direct</div>
          {contacts.length === 0 && (
            <div className="px-4 py-2 text-[11px] text-[#444]">No users found.</div>
          )}
          {contacts.map(c => (
            <SidebarItem key={c.id} id={c.id} name={c.username} type="personal" />
          ))}

          {groups.length > 0 && (
            <>
              <div className="px-4 pt-5 pb-1 text-[10px] text-[#444] uppercase tracking-widest">Groups</div>
              {groups.map(g => (
                <SidebarItem key={g.id} id={g.id} name={g.name} type="group" />
              ))}
            </>
          )}
        </div>
      </div>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col bg-white border-l border-[#e8e4df]">
        {view === "settings" ? (
          <SettingsPanel
            user={user}
            onUsernameChange={handleUsernameChange}
            onClose={() => setView("chat")}
          />
        ) : selected ? (
          <ChatPanel user={user} selected={selected} messages={messages} ws={ws} />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl text-[#e0ddd9] mb-2">◼</div>
              <div className="text-xs text-[#bbb]">Select a contact to start chatting.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ROOT
// ─────────────────────────────────────────────────────────────────────────────
export default function App() {
  // user = null | { id, username }
  const [user, setUser] = useState(null);

  const handleLogin = async (userId) => {
    // Fetch all users to find current user's username
    try {
      const d = await api("/get_all_users");
      const me = (d.users ?? []).find(u => u.id === userId);
      setUser({ id: userId, username: me?.username ?? null });
    } catch {
      setUser({ id: userId, username: null });
    }
  };

  if (!user) return <LoginScreen onLogin={handleLogin} />;

  if (!user.username)
    return (
      <SetUsernameScreen
        userId={user.id}
        onDone={(username) => setUser({ ...user, username })}
      />
    );

  return (
    <MainApp
      user={user}
      onUsernameChange={(username) => setUser({ ...user, username })}
    />
  );
}
