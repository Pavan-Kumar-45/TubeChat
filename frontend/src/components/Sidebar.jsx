import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useChats } from '../context/ChatContext';
import {
  Plus, MessageSquare, Trash2, Pencil, Check, X,
  Sun, Moon, LogOut, PanelLeftClose, PanelLeft,
  Youtube,
} from 'lucide-react';
import clsx from 'clsx';

/**
 * Collapsible sidebar showing the chat list, new-chat button,
 * theme toggle, and logout. Displays a pulsing dot on chats with active streams.
 */
export default function Sidebar() {
  const { logout } = useAuth();
  const { dark, toggle } = useTheme();
  const { chatList, refresh, remove, rename, getChatState } = useChats();
  const navigate = useNavigate();
  const location = useLocation();

  const [open, setOpen] = useState(true);
  const [editId, setEditId] = useState(null);
  const [editVal, setEditVal] = useState('');
  const editRef = useRef(null);

  useEffect(() => { refresh(); }, [refresh]);

  /* save rename */
  const saveRename = async () => {
    if (editVal.trim() && editId) {
      await rename(editId, editVal.trim());
    }
    setEditId(null);
  };

  /* start rename */
  const startRename = (chat) => {
    setEditId(chat.id);
    setEditVal(chat.name || chat.title || '');
    setTimeout(() => editRef.current?.focus(), 0);
  };

  /* ── Collapsed ── */
  if (!open) {
    return (
      <div className="w-[52px] border-r border-[var(--color-border)] bg-[var(--color-sidebar)] flex flex-col items-center py-3 gap-2 shrink-0">
        <button onClick={() => setOpen(true)} className="p-2 rounded-lg hover:bg-[var(--color-hover)] text-[var(--color-text-secondary)]">
          <PanelLeft size={18} />
        </button>
        <button onClick={() => navigate('/')} className="p-2 rounded-lg hover:bg-[var(--color-hover)] text-[var(--color-text-secondary)]">
          <Plus size={18} />
        </button>
      </div>
    );
  }

  /* ── Expanded ── */
  return (
    <div className="w-64 border-r border-[var(--color-border)] bg-[var(--color-sidebar)] flex flex-col shrink-0">
      {/* Header */}
      <div className="h-14 px-3 flex items-center justify-between border-b border-[var(--color-border)]">
        <Link to="/" className="flex items-center gap-2 font-semibold text-sm">
          <Youtube size={20} className="text-red-500" />
          <span>TubeChat AI</span>
        </Link>
        <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-[var(--color-hover)] text-[var(--color-text-secondary)]">
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* New Chat */}
      <div className="px-3 pt-3 pb-1">
        <button
          onClick={() => navigate('/')}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed border-[var(--color-border)] hover:bg-[var(--color-hover)] text-sm font-medium text-[var(--color-text-secondary)] transition-colors"
        >
          <Plus size={16} /> New Chat
        </button>
      </div>

      {/* Chat list */}
      <nav className="flex-1 overflow-y-auto no-scrollbar px-2 py-2 space-y-0.5">
        {chatList.map(chat => {
          const active = location.pathname === `/chat/${chat.id}`;
          const isEditing = editId === chat.id;
          const chatState = getChatState(chat.id);
          const isStreaming = chatState.status !== 'idle';

          return (
            <div
              key={chat.id}
              className={clsx(
                'group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors',
                active
                  ? 'bg-[var(--color-hover)] text-[var(--color-text)]'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-hover)] hover:text-[var(--color-text)]'
              )}
              onClick={() => !isEditing && navigate(`/chat/${chat.id}`)}
            >
              <MessageSquare size={14} className="shrink-0 opacity-50" />

              {isEditing ? (
                <form onSubmit={e => { e.preventDefault(); saveRename(); }} className="flex-1 flex items-center gap-1">
                  <input
                    ref={editRef}
                    value={editVal}
                    onChange={e => setEditVal(e.target.value)}
                    className="flex-1 bg-transparent outline-none text-sm min-w-0"
                    onBlur={saveRename}
                  />
                  <button type="submit" className="p-0.5"><Check size={12} className="text-green-500" /></button>
                  <button type="button" onClick={() => setEditId(null)} className="p-0.5"><X size={12} className="text-red-400" /></button>
                </form>
              ) : (
                <>
                  <span className="flex-1 truncate">{chat.name || chat.title || 'Untitled'}</span>
                  {isStreaming && (
                    <span className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-pulse shrink-0" title="Generating..." />
                  )}
                  <div className="hidden group-hover:flex items-center gap-0.5">
                    <button onClick={e => { e.stopPropagation(); startRename(chat); }} className="p-1 rounded hover:bg-[var(--color-border)]">
                      <Pencil size={12} />
                    </button>
                    <button onClick={e => { e.stopPropagation(); remove(chat.id); if (active) navigate('/'); }} className="p-1 rounded hover:bg-[var(--color-border)] text-red-400">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-[var(--color-border)] p-3 flex items-center justify-between">
        <button onClick={toggle} className="p-2 rounded-lg hover:bg-[var(--color-hover)] text-[var(--color-text-secondary)]" title="Toggle theme">
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button onClick={logout} className="p-2 rounded-lg hover:bg-[var(--color-hover)] text-[var(--color-text-secondary)]" title="Log out">
          <LogOut size={16} />
        </button>
      </div>
    </div>
  );
}
