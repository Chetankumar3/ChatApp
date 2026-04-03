import {
  createContext, useContext, useState, useEffect,
  useRef, useCallback,
} from 'react';
import { useAuth } from './AuthContext.jsx';
import { getAllConversations } from '../api/users.js';
import { nowISO } from '../utils/time.js';

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const { userId } = useAuth();

  // { [otherId]: { user: {id,username,name,...}, messages: [] } }
  const [directConvs, setDirectConvs]   = useState({});
  // { [groupId]: { group: {id,name,...}, messages: [] } }
  const [groupConvs, setGroupConvs]     = useState({});
  // { type: 'direct'|'group', id: number } | null
  const [activeConv, setActiveConv]     = useState(null);
  const [chatLoading, setChatLoading]   = useState(false);

  const wsRef             = useRef(null);
  const shouldConnectRef  = useRef(false);
  const reconnectTimer    = useRef(null);

  // ─── Hydrate ────────────────────────────────────────────────────────────────
  const hydrate = useCallback(async () => {
    if (!userId) return;
    setChatLoading(true);
    try {
      const data = await getAllConversations(userId);

      const userMap  = {};
      const groupMap = {};

      (data.associated_users || []).forEach((u) => { userMap[u.id] = u; });
      (data.associated_groups || []).forEach((g) => { groupMap[g.id] = g; });

      // Build direct conversations
      const directs = {};
      (data.direct_messages || []).forEach((m) => {
        const otherId = m.fromId === userId ? m.toId : m.fromId;
        if (!directs[otherId]) {
          directs[otherId] = { user: userMap[otherId] || { id: otherId }, messages: [] };
        }
        directs[otherId].messages.push(m);
      });

      // Build group conversations
      const groups = data.associated_groups.reduce((acc, g) => {
        acc[g.id] = { group: g, messages: [] };
        return acc;
      }, {});
      const rawGroups = data.group_messages || {};
      Object.entries(rawGroups).forEach(([gid, msgs]) => {
        const id = Number(gid);
        groups[id] = { group: groupMap[id] || { id, name: `Group ${id}` }, messages: msgs || [] };
      });

      setDirectConvs(directs);
      setGroupConvs(groups);
    } catch (e) {
      console.error('hydrate failed', e);
    } finally {
      setChatLoading(false);
    }
  }, [userId]);

  // ─── WebSocket ──────────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (!shouldConnectRef.current || !userId) return;

    const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${WS_BASE}/ws/${userId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'direct_message') {
          const otherId = msg.fromId === userId ? msg.toId : msg.fromId;
          setDirectConvs((prev) => {
            const conv = prev[otherId] || { user: { id: otherId }, messages: [] };
            return { ...prev, [otherId]: { ...conv, messages: [...conv.messages, msg] } };
          });
        } else if (msg.type === 'group_message') {
          setGroupConvs((prev) => {
            const conv = prev[msg.toId] || { group: { id: msg.toId }, messages: [] };
            return { ...prev, [msg.toId]: { ...conv, messages: [...conv.messages, msg] } };
          });
        }
      } catch (e) {
        console.warn('WS parse error', e);
      }
    };

    ws.onclose = () => {
      if (!shouldConnectRef.current) return;
      reconnectTimer.current = setTimeout(connectWS, 3000);
    };

    ws.onerror = () => ws.close();
  }, [userId]);

  useEffect(() => {
    if (!userId) return;
    shouldConnectRef.current = true;
    hydrate();
    connectWS();
    return () => {
      shouldConnectRef.current = false;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [userId, hydrate, connectWS]);

  // ─── Send ────────────────────────────────────────────────────────────────────
  const sendMessage = useCallback((convType, toId, body) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;

    const msg = {
      type:    convType === 'direct' ? 'direct_message' : 'group_message',
      fromId:  userId,
      toId:    Number(toId),
      body,
      sentAt:  nowISO(),
    };

    ws.send(JSON.stringify(msg));

    // Optimistic update
    if (convType === 'direct') {
      setDirectConvs((prev) => {
        const conv = prev[toId] || { user: { id: toId }, messages: [] };
        return { ...prev, [toId]: { ...conv, messages: [...conv.messages, msg] } };
      });
    } else {
      setGroupConvs((prev) => {
        const conv = prev[toId] || { group: { id: toId }, messages: [] };
        return { ...prev, [toId]: { ...conv, messages: [...conv.messages, msg] } };
      });
    }
    return true;
  }, [userId]);

  // ─── Add direct conv without message (new friend) ────────────────────────────
  const openDirectConv = useCallback((user) => {
    setDirectConvs((prev) => {
      if (prev[user.id]) return prev;
      return { ...prev, [user.id]: { user, messages: [] } };
    });
    setActiveConv({ type: 'direct', id: user.id });
  }, []);

  // ─── Add group conv after creation ──────────────────────────────────────────
  const addGroupConv = useCallback((group) => {
    setGroupConvs((prev) => ({
      ...prev,
      [group.id]: { group, messages: [] },
    }));
    setActiveConv({ type: 'group', id: group.id });
  }, []);

  const removeGroupConv = useCallback((groupId) => {
    setGroupConvs((prev) => {
      const next = { ...prev };
      delete next[groupId];
      return next;
    });
    setActiveConv((a) => (a?.type === 'group' && a.id === groupId ? null : a));
  }, []);

  return (
    <ChatContext.Provider value={{
      directConvs, setDirectConvs,
      groupConvs,  setGroupConvs,
      activeConv,  setActiveConv,
      chatLoading,
      sendMessage,
      openDirectConv,
      addGroupConv,
      removeGroupConv,
      hydrate,
    }}>
      {children}
    </ChatContext.Provider>
  );
}

export const useChat = () => useContext(ChatContext);
