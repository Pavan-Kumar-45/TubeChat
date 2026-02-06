import { createContext, useContext, useEffect, useState } from 'react';

const Ctx = createContext(null);

/**
 * Provides dark/light theme state and a toggle function.
 * Persists the preference to localStorage and syncs with the `dark` CSS class.
 */
export function ThemeProvider({ children }) {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return true;
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  const toggle = () => setDark(d => !d);

  return <Ctx.Provider value={{ dark, toggle }}>{children}</Ctx.Provider>;
}

/** Hook to access theme context (dark, toggle). */
export const useTheme = () => useContext(Ctx);
