import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { chats as chatsApi } from '../lib/api';
import { useChats } from '../context/ChatContext';
import { Youtube, ArrowRight, Loader2 } from 'lucide-react';

/**
 * Landing page where users paste a YouTube URL to start a new chat.
 * Includes feature cards and handles chat creation with loading/error states.
 */
export default function HomePage() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { refresh } = useChats();

  const submit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError('');
    try {
      const chat = await chatsApi.create(url.trim());
      await refresh();
      navigate(`/chat/${chat.id}`);
    } catch (err) {
      setError(err.message || 'Failed to create chat');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-xl w-full text-center space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg">
            <Youtube size={28} className="text-white" />
          </div>
        </div>

        {/* Title */}
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">What do you want to learn?</h1>
          <p className="text-[var(--color-text-secondary)]">
            Paste a YouTube link and start chatting with the video.
          </p>
        </div>

        {/* URL Input */}
        <form onSubmit={submit} className="space-y-3">
          <div className="flex items-center gap-2 bg-[var(--color-input-bg)] border border-[var(--color-border)] rounded-xl px-4 py-3 focus-within:border-[var(--color-accent)] transition-colors">
            <Youtube size={18} className="text-red-500 shrink-0" />
            <input
              type="text"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="flex-1 bg-transparent outline-none text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-secondary)]"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!url.trim() || loading}
              className="w-8 h-8 rounded-lg bg-[var(--color-accent)] text-white flex items-center justify-center hover:bg-[var(--color-accent-hover)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
            </button>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </form>
      </div>
    </div>
  );
}
