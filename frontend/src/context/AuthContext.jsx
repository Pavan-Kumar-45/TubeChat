import { createContext, useContext, useState, useEffect } from 'react';
import { auth as authApi } from '../lib/api';

const Ctx = createContext(null);

/**
 * Provides authentication state (user, loading) and actions (login, register, logout)
 * to all child components via React context.
 */
export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    authApi.me()
      .then(setUser)
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username, password) => {
    const data = await authApi.login({ username, password });
    localStorage.setItem('token', data.access_token);
    const me = await authApi.me();
    setUser(me);
    return me;
  };

  const register = (username, password) =>
    authApi.register({ username, password });

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <Ctx.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </Ctx.Provider>
  );
}

/** Hook to access authentication context (user, login, register, logout). */
export const useAuth = () => useContext(Ctx);
