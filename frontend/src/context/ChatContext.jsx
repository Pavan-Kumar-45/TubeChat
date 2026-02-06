import { createContext, useCallback, useContext, useRef, useState } from 'react';
import { chats as chatsApi, streamQuestion } from '../lib/api';

const Ctx = createContext(null);

/**
 * Global chat state provider. Stores per-chat state (messages, status, chatInfo)
 * in a ref-backed map so streaming callbacks always see the latest values.
 * Re-renders are triggered by bumping a counter state.
 */
export function ChatProvider({ children }) {
  const [chatList, setChatList] = useState([]);

  /*
   * Per-chat state map:
   *   { [chatId]: { messages: [], status: 'idle' | string, chatInfo: null | obj, loaded: bool } }
   * Stored in a ref so streaming callbacks always see the latest value,
   * with a companion state counter to trigger re-renders.
   */
  const chatStates = useRef({});
  const [, bump]   = useState(0);
  const forceUpdate = useCallback(() => bump(n => n + 1), []);

  /* helper: get or create per-chat entry */
  const getChat = useCallback((id) => {
    const key = String(id);
    if (!chatStates.current[key]) {
      chatStates.current[key] = { messages: [], status: 'idle', chatInfo: null, loaded: false };
    }
    return chatStates.current[key];
  }, []);

  /* helper: mutate per-chat entry and re-render */
  const updateChat = useCallback((id, updater) => {
    const entry = getChat(id);
    updater(entry);
    forceUpdate();
  }, [getChat, forceUpdate]);

  /* ── Chat list CRUD ── */
  const refresh = useCallback(async () => {
    try { setChatList(await chatsApi.list()); } catch { /* logged out */ }
  }, []);

  const remove = useCallback(async (id) => {
    await chatsApi.del(id);
    setChatList(prev => prev.filter(c => c.id !== id));
    delete chatStates.current[String(id)];
    forceUpdate();
  }, [forceUpdate]);

  const rename = useCallback(async (id, name) => {
    await chatsApi.rename(id, name);
    setChatList(prev => prev.map(c => c.id === id ? { ...c, name } : c));
  }, []);

  /* ── Load chat info + history (idempotent) ── */
  const loadChat = useCallback(async (id) => {
    const entry = getChat(id);
    if (entry.loaded || entry._loading) return;   // already loaded or in-flight
    entry._loading = true;

    try {
      const [info, msgs] = await Promise.all([
        chatsApi.get(id).catch(() => null),
        chatsApi.messages(id).catch(() => []),
      ]);
      updateChat(id, (e) => {
        e.chatInfo = info;
        // only set messages if no streaming has started (don't overwrite live data)
        if (e.messages.length === 0) {
          e.messages = msgs.map(m => ({
            role: m.role,
            content: m.content,
            followUp: m.follow_up || [],
          }));
        }
        e.loaded = true;
        e._loading = false;
      });
    } catch {
      entry._loading = false;
    }
  }, [getChat, updateChat]);

  /* ── Send a question (survives navigation) ── */
  const sendMessage = useCallback(async (id, question) => {
    const entry = getChat(id);
    // don't allow sending if already streaming
    if (entry.status !== 'idle') return;

    updateChat(id, (e) => {
      e.messages = [...e.messages, { role: 'user', content: question }];
      e.status = 'Thinking...';
    });

    await streamQuestion(
      id,
      question,
      /* onStatus */ (msg) => {
        updateChat(id, (e) => { e.status = msg; });
      },
      /* onResult */ (payload) => {
        updateChat(id, (e) => {
          e.messages = [
            ...e.messages,
            {
              role: 'ai',
              content: payload.answer,
              followUp: payload.follow_up || [],
            },
          ];
          e.status = 'idle';
        });
        refresh();
      },
      /* onError */ (msg) => {
        updateChat(id, (e) => {
          e.messages = [
            ...e.messages,
            { role: 'ai', content: `⚠️ Error: ${msg}` },
          ];
          e.status = 'idle';
        });
      },
    );
  }, [getChat, updateChat, refresh]);

  /* ── Exposed per-chat hook data ── */
  const getChatState = useCallback((id) => {
    return getChat(id);
  }, [getChat]);

  return (
    <Ctx.Provider value={{ chatList, refresh, remove, rename, loadChat, sendMessage, getChatState }}>
      {children}
    </Ctx.Provider>
  );
}

/** Hook to access chat context (chatList, refresh, remove, rename, loadChat, sendMessage, getChatState). */
export const useChats = () => useContext(Ctx);
