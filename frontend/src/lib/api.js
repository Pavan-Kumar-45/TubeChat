const BASE = '/api';

/**
 * Make an authenticated JSON request to the backend API.
 * @param {'GET'|'POST'|'PUT'|'DELETE'} method - HTTP method.
 * @param {string} path - API path (appended to /api).
 * @param {object|null} body - Request body (serialised to JSON).
 * @returns {Promise<object>} Parsed JSON response.
 * @throws {Error} If the response is not OK.
 */
async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('token');
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : null,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  get:  (path)        => request('GET', path),
  post: (path, body)  => request('POST', path, body),
  put:  (path, body)  => request('PUT', path, body),
  del:  (path)        => request('DELETE', path),
};

/* ── Auth ── */
export const auth = {
  login:    (data) => api.post('/auth/token', data),
  register: (data) => api.post('/auth/register', data),
  me:       ()     => api.get('/user/me'),
};

/* ── Chats ── */
export const chats = {
  list:       ()         => api.get('/chat/list'),
  create:     (url)      => api.post('/chat/create', { url }),
  get:        (id)       => api.get(`/chat/get/${id}`),
  del:        (id)       => api.del(`/chat/delete/${id}`),
  rename:     (id, name) => api.put(`/chat/update_name/${id}`, { name }),
  messages:   (id)       => api.get(`/chat/${id}/messages`),
};

/* ── Stream (SSE via fetch) ── */
/**
 * Stream an AI response for a question via Server-Sent Events.
 * @param {number} chatId - Chat session ID.
 * @param {string} question - The user's question.
 * @param {(msg: string) => void} onStatus - Called with status updates.
 * @param {(payload: object) => void} onResult - Called with the final result payload.
 * @param {(msg: string) => void} onError - Called on error.
 */
export async function streamQuestion(chatId, question, onStatus, onResult, onError) {
  const token = localStorage.getItem('token');
  const res = await fetch(`${BASE}/stream/${chatId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Stream failed' }));
    onError(err.detail || `HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      if (!part.startsWith('data: ')) continue;
      try {
        const data = JSON.parse(part.slice(6));
        if (data.type === 'status') onStatus(data.msg);
        else if (data.type === 'result') onResult(data.payload);
        else if (data.type === 'error') onError(data.msg);
      } catch { /* partial JSON, skip */ }
    }
  }
}
