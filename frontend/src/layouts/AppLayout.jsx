import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

/**
 * Root layout for authenticated pages. Renders the sidebar and
 * a main content area with a React Router Outlet.
 */
export default function AppLayout() {
  return (
    <div className="h-screen flex bg-[var(--color-bg)] text-[var(--color-text)] overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
