import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ChatProvider } from './context/ChatContext';

import AppLayout from './layouts/AppLayout';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

/* ── Route guards ── */
/**
 * Route guard that redirects unauthenticated users to /login.
 * Shows a spinner while auth state is loading.
 */
function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-[var(--color-bg)]">
      <div className="w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
    </div>
  );
  return user ? children : <Navigate to="/login" replace />;
}

/**
 * Route guard that redirects authenticated users to /.
 * Allows only unauthenticated access.
 */
function GuestOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/" replace /> : children;
}

/**
 * Root application component. Sets up providers (Theme, Auth, Chat)
 * and defines all routes with auth guards.
 */
export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ChatProvider>
          <BrowserRouter>
            <Routes>
              {/* Auth */}
              <Route path="/login"    element={<GuestOnly><LoginPage /></GuestOnly>} />
              <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />

              {/* App */}
              <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
                <Route index element={<HomePage />} />
                <Route path="/chat/:id" element={<ChatPage />} />
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </ChatProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
