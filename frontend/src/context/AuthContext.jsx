import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { isSessionValid } from '../utils/time.js';
import { getUserInfo } from '../api/users.js';

const AuthContext = createContext(null);
const TOKEN_KEY = 'ping_token';

function decodeJWT(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [userId, setUserId]   = useState(null);
  const [me, setMe]           = useState(null); // full user object
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token) {
          const payload = decodeJWT(token);
          if (payload && payload.exp * 1000 > Date.now()) {
            const id = payload.user_id;
            setUserId(id);
            const info = await getUserInfo(id).catch(() => null);
            setMe(info);
          } else {
            localStorage.removeItem(TOKEN_KEY);
          }
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (token, isNewUser) => {
    localStorage.setItem(TOKEN_KEY, token);
    const payload = decodeJWT(token);
    const id = payload.user_id;
    setUserId(id);
    const info = await getUserInfo(id).catch(() => null);
    setMe(info);
    return { userId: id, isNewUser };
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
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
