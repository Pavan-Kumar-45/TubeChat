import { useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useChats } from '../context/ChatContext';
import MessageBubble, { ThinkingBubble } from '../components/MessageBubble';
import ChatInput from '../components/ChatInput';
import { Youtube, ExternalLink, CheckCircle2, User, Loader2 } from 'lucide-react';

/* ── Video Info Card (always inside the scroll area) ── */
/**
 * Compact card displaying the YouTube video thumbnail, title, author,
 * and a link to watch on YouTube. Always rendered as the first item
 * inside the scrollable message area.
 */
function VideoCard({ chat }) {
  if (!chat) return null;
  return (
    <div className="animate-fade-up max-w-[240px] mx-auto">
      <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden shadow-sm">
        {chat.thumbnail_url && (
          <div className="relative group">
            <img
              src={chat.thumbnail_url}
              alt={chat.title || 'Video thumbnail'}
              className="w-full aspect-video object-cover"
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
              <a
                href={chat.url}
                target="_blank"
                rel="noopener noreferrer"
                className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 text-black px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5"
              >
                <ExternalLink size={12} /> Watch on YouTube
              </a>
            </div>
          </div>
        )}
        <div className="p-4 space-y-3">
          <div className="flex items-start gap-2">
            <CheckCircle2 size={16} className="text-green-500 shrink-0 mt-0.5" />
            <div className="space-y-1 min-w-0">
              <p className="text-sm font-semibold leading-snug line-clamp-2">{chat.title || 'Untitled Video'}</p>
              {chat.author && (
                <p className="text-xs text-[var(--color-text-secondary)] flex items-center gap-1">
                  <User size={10} /> {chat.author}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 pt-1 border-t border-[var(--color-border)]">
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-green-600 dark:text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
              <CheckCircle2 size={10} /> Video loaded
            </span>
            <span className="text-[10px] text-[var(--color-text-secondary)]">Ready to chat</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Main chat view. Loads chat info and message history, displays them
 * in a scrollable area, streams AI responses, and blocks input until ready.
 */
export default function ChatPage() {
  const { id } = useParams();
  const { chatList, loadChat, sendMessage, getChatState } = useChats();
  const scrollRef = useRef(null);

  /* read per-chat state from global store */
  const chatState = getChatState(id);
  const { messages, status, chatInfo, loaded } = chatState;
  const chat = chatInfo || chatList.find(c => c.id === Number(id));
  const busy = status !== 'idle';
  const ready = loaded && !!chat;         // chat info loaded from API

  /* load chat info + history on mount / id change */
  useEffect(() => {
    loadChat(id);
  }, [id, loadChat]);

  /* auto-scroll when messages or status change */
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  /* send handler */
  const send = useCallback((question) => {
    sendMessage(id, question);
  }, [id, sendMessage]);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <header className="h-12 border-b border-[var(--color-border)] flex items-center px-4 gap-3 shrink-0">
        <Youtube size={16} className="text-red-500 shrink-0" />
        <p className="text-sm font-medium truncate">{chat?.title || chat?.name || 'Chat'}</p>
        {chat?.author && (
          <span className="text-xs text-[var(--color-text-secondary)] hidden sm:block">by {chat.author}</span>
        )}
        {/* Loading status badge in header */}
        {!ready && (
          <span className="ml-auto inline-flex items-center gap-1.5 text-[11px] text-[var(--color-text-secondary)] animate-pulse">
            <Loader2 size={12} className="animate-spin" /> Loading…
          </span>
        )}
        {ready && (
          <span className="ml-auto inline-flex items-center gap-1 text-[10px] font-medium text-green-600 dark:text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">
            <CheckCircle2 size={10} /> Ready
          </span>
        )}
      </header>

      {/* Messages area (scrollable — VideoCard is the first item) */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {/* Loading skeleton */}
          {!loaded && (
            <div className="py-12 flex items-center justify-center">
              <span className="text-sm text-[var(--color-text-secondary)] animate-pulse">Loading messages…</span>
            </div>
          )}

          {/* Video card — always first in scroll when chat is loaded */}
          {loaded && chat && (
            <div className={messages.length === 0 ? 'py-8' : 'pb-2'}>
              <VideoCard chat={chat} />
              {messages.length === 0 && (
                <p className="text-center text-xs text-[var(--color-text-secondary)] mt-4">
                  Ask anything about this video below.
                </p>
              )}
            </div>
          )}

          {/* Chat messages */}
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              followUp={msg.followUp}
              onFollowUp={ready && !busy ? send : undefined}
            />
          ))}

          {busy && <ThinkingBubble status={status} />}

          <div ref={scrollRef} />
        </div>
      </div>

      {/* Input — blocked until chat is ready */}
      <ChatInput onSend={send} disabled={busy || !ready} />
    </div>
  );
}
