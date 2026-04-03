import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { isSessionValid } from '../utils/time.js';
import { getUserInfo } from '../api/users.js';

const AuthContext = createContext(null);
const STORAGE_KEY = 'ping_session';

export function AuthProvider({ children }) {
  const [userId, setUserId]   = useState(null);
  const [me, setMe]           = useState(null); // full user object
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    (async () => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const { userId: id, loginTime } = JSON.parse(raw);
          if (isSessionValid(loginTime)) {
            setUserId(id);
            const info = await getUserInfo(id).catch(() => null);
            setMe(info);
          } else {
            localStorage.removeItem(STORAGE_KEY);
          }
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (id) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ userId: id, loginTime: Date.now() }));
    setUserId(id);
    const info = await getUserInfo(id).catch(() => null);
    setMe(info);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUserId(null);
    setMe(null);
  }, []);

  const refreshMe = useCallback(async () => {
    if (!userId) return;
    const info = await getUserInfo(userId).catch(() => null);
    setMe(info);
  }, [userId]);

  return (
    <AuthContext.Provider value={{ userId, me, login, logout, loading, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
