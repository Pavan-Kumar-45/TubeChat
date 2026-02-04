import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Youtube, LogOut, MessageSquare, Menu, X, Moon, Sun, Sparkles } from 'lucide-react';
import { Button } from './ui';
import { useState, useEffect } from 'react';
import { cn } from '../utils';
import { chatService } from '../services/api';

export const Layout = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [recentChats, setRecentChats] = useState([]);

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const chats = await chatService.getUserChats();
        setRecentChats(chats.slice(0, 5)); // Show only 5 most recent
      } catch (error) {
        console.error('Failed to fetch chats:', error);
      }
    };
    if (user) {
      fetchChats();
    }
  }, [user, location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen w-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex flex-col w-72 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-lg">
        <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
          <Link to="/" className="flex items-center gap-3 font-bold text-2xl hover:opacity-80 transition-all group">
            <div className="w-10 h-10 bg-red-600 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform shadow-lg shadow-red-600/30">
              <svg className="w-6 h-6" viewBox="0 0 159 110" fill="none">
                <path d="M64 69.5L103 47L64 24.5V69.5Z" fill="white"/>
              </svg>
            </div>
            <span className="text-zinc-900 dark:text-white">TubeChat AI</span>
          </Link>
          <p className="text-xs text-zinc-500 mt-2 ml-[52px]">Chat with YouTube videos</p>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
          <Link to="/" className="block">
            <Button
              variant={location.pathname === '/' ? "primary" : "ghost"}
              className="w-full justify-start gap-3 text-left bg-red-600 hover:bg-red-700 text-white"
            >
              <MessageSquare className="w-5 h-5" />
              <span className="font-medium">New Chat</span>
            </Button>
          </Link>
          
          <div className="pt-6 pb-2 px-3 text-xs font-bold text-zinc-500 dark:text-zinc-600 uppercase tracking-wider">
            Recent Sessions
          </div>
          
          <div className="space-y-1 px-2">
            {recentChats.length === 0 ? (
              <p className="py-2 text-center italic text-sm text-zinc-500 dark:text-zinc-600">No recent chats</p>
            ) : (
              recentChats.map((chat) => (
                <Link
                  key={chat.id}
                  to={`/chat/${chat.id}`}
                  className="block px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors truncate"
                >
                  {chat.name || chat.title || 'Untitled Chat'}
                </Link>
              ))
            )}
          </div>
        </nav>

        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950">
          <div className="flex items-center gap-3 px-3 py-3 mb-3 rounded-xl bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
            <div className="w-10 h-10 rounded-full bg-red-600 flex items-center justify-center text-white text-sm font-bold shadow-lg">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-semibold truncate text-zinc-900 dark:text-zinc-100">{user?.username}</p>
              <p className="text-xs text-zinc-500">Active</p>
            </div>
          </div>
          
          <div className="flex gap-2">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={toggleTheme} 
              className="flex-1 gap-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-800"
              title={theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
            <Button 
              variant="ghost" 
              onClick={handleLogout} 
              className="flex-1 gap-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-sm font-medium">Sign Out</span>
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full relative">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-zinc-900 dark:text-white">
            <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5" viewBox="0 0 159 110" fill="none">
                <path d="M64 69.5L103 47L64 24.5V69.5Z" fill="white"/>
              </svg>
            </div>
            <span>TubeChat AI</span>
          </Link>
          <div className="flex items-center gap-2">
            <button 
              onClick={toggleTheme}
              className="p-2 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
              className="p-2 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </header>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="absolute inset-0 z-50 bg-white dark:bg-slate-950 p-4 md:hidden flex flex-col animate-slide-down">
             <div className="flex justify-between items-center mb-8 pb-4 border-b border-slate-200 dark:border-slate-800">
                <span className="text-xl font-bold flex gap-2 items-center">
                  <Youtube className="text-primary-500" /> 
                  <span>Menu</span>
                </span>
                <button onClick={() => setMobileMenuOpen(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg">
                  <X />
                </button>
             </div>
             
             <div className="flex items-center gap-3 p-4 mb-6 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white font-bold">
                  {user?.username?.[0]?.toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold">{user?.username}</p>
                  <p className="text-xs text-slate-500">Active</p>
                </div>
             </div>

             <nav className="flex-1 space-y-3">
               <Link to="/" onClick={() => setMobileMenuOpen(false)}>
                  <Button className="w-full justify-start gap-3" variant="secondary">
                    <MessageSquare className="w-5 h-5" />
                    New Chat
                  </Button>
               </Link>
             </nav>

             <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
               <Button 
                 variant="ghost" 
                 onClick={handleLogout} 
                 className="w-full justify-start gap-3 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10"
               >
                 <LogOut className="w-5 h-5" />
                 Sign Out
               </Button>
             </div>
          </div>
        )}

        <div className="flex-1 overflow-hidden relative">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
