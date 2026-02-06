<div align="center">

# 🎬 TubeChat AI

**Chat with any YouTube video using AI-powered RAG**

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-1c3c3c?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-AI-4285f4?logo=google&logoColor=white)](https://ai.google.dev)

Paste a YouTube URL → AI extracts the transcript → Ask anything about the video

</div>

---

## ✨ Features

- 🔍 **RAG Pipeline** — Retrieves relevant transcript chunks via ChromaDB vector similarity search
- 🧠 **Multi-Node AI Graph** — LangGraph pipeline: Reformulate → Retrieve → Draft → Judge → (Tavily fallback) → Generate
- 💬 **Conversational Memory** — Summary buffer keeps context across long conversations without token bloat
- 🔄 **Query Reformulation** — Resolves pronouns and vague references using conversation history
- 🌐 **Web Fallback** — Tavily search kicks in when transcript context isn't sufficient
- ⚡ **Real-time Streaming** — Server-Sent Events stream pipeline status and AI responses live
- 🎨 **Modern UI** — GPT/Claude-inspired design with dark/light mode, markdown rendering, syntax highlighting
- 🔐 **JWT Authentication** — Secure user accounts with bcrypt-hashed passwords
- 📝 **Chat Persistence** — Full message history saved to MySQL, survives page refreshes
- 🗂️ **Multi-Chat** — Manage multiple video conversations in a collapsible sidebar

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React 19)                  │
│  Vite 7 · Tailwind CSS v4 · React Router · SSE Client   │
└────────────────────────┬────────────────────────────────┘
                         │ /api proxy
┌────────────────────────▼────────────────────────────────┐
│                   Backend (FastAPI)                       │
│          JWT Auth · SQLAlchemy ORM · MySQL                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              LangGraph AI Pipeline                       │
│                                                          │
│  START → REFORMULATE → RETRIEVER → AGENT → JUDGE        │
│                                      │                   │
│                              ┌───────┴───────┐           │
│                              │               │           │
│                         is_good=true    is_good=false     │
│                              │               │           │
│                              │        SEARCH_TAVILY      │
│                              │               │           │
│                              │         FINAL_AGENT       │
│                              │               │           │
│                              └───────┬───────┘           │
│                                      │                   │
│                              GENERATE_ANSWER → END       │
│                                                          │
│  Google Gemini · ChromaDB · Tavily Search                │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Youtube-Rag/
├── backend/
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── db.py                # SQLAlchemy engine & session factory
│   ├── schemas.py           # ORM models (User, Chat, Message)
│   ├── models.py            # Pydantic request/response schemas
│   ├── agents.py            # LangGraph nodes, vector store, LLM calls
│   ├── graph.py             # StateGraph workflow compilation & caching
│   └── routers/
│       ├── auth.py          # JWT login/register, password hashing
│       ├── user.py          # User profile & chat listing
│       ├── chat.py          # Chat CRUD, YouTube URL validation
│       └── stream.py        # SSE streaming endpoint, memory buffer
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Root component, providers, route guards
│   │   ├── main.jsx         # React DOM entry point
│   │   ├── index.css        # Tailwind v4 theme, prose overrides, animations
│   │   ├── lib/api.js       # Fetch-based API client, SSE stream handler
│   │   ├── context/
│   │   │   ├── AuthContext.jsx   # Auth state & login/logout actions
│   │   │   ├── ThemeContext.jsx  # Dark/light mode toggle
│   │   │   └── ChatContext.jsx   # Global per-chat state (ref-backed)
│   │   ├── components/
│   │   │   ├── Sidebar.jsx       # Collapsible chat list, rename, delete
│   │   │   ├── ChatInput.jsx     # Auto-grow textarea, send controls
│   │   │   └── MessageBubble.jsx # Markdown rendering, code blocks, copy
│   │   ├── pages/
│   │   │   ├── HomePage.jsx      # URL input, feature cards
│   │   │   ├── ChatPage.jsx      # Chat view, video card, streaming
│   │   │   ├── LoginPage.jsx     # Sign in form
│   │   │   └── RegisterPage.jsx  # Sign up form
│   │   └── layouts/
│   │       └── AppLayout.jsx     # Sidebar + outlet wrapper
│   └── vite.config.js       # Vite + Tailwind plugin + API proxy
├── requirements.txt
├── .env                     # API keys & DB config (gitignored)
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **MySQL** running locally
- API keys for **Google Gemini** and **Tavily Search**

### 1. Clone the repository

```bash
git clone https://github.com/Pavan-Kumar-45/Youtube-Rag.git
cd Youtube-Rag
```

### 2. Set up the backend

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
api_key=YOUR_GOOGLE_GEMINI_API_KEY
tavily_key=YOUR_TAVILY_API_KEY
SECRET_KEY=YOUR_JWT_SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DB_URL=mysql+pymysql://root:yourpassword@localhost:3306/yt_rag
```

> Generate a secure `SECRET_KEY` with: `python -c "import secrets; print(secrets.token_hex(32))"`

### 4. Create the MySQL database

```sql
CREATE DATABASE yt_rag;
```

> Tables are auto-created by SQLAlchemy on first startup.

### 5. Set up the frontend

```bash
cd frontend
npm install
```

### 6. Run the application

Open two terminals:

**Terminal 1 — Backend:**
```bash
uvicorn backend.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | REST API framework |
| LangGraph | Multi-node AI agent pipeline |
| LangChain | LLM orchestration & document loading |
| Google Gemini | LLM for generation & evaluation |
| Google Gemini Embeddings | Text embeddings |
| ChromaDB | Vector store for transcript chunks |
| Tavily Search | Web search fallback |
| SQLAlchemy + PyMySQL | ORM & MySQL connection |
| python-jose + bcrypt | JWT auth & password hashing |
| pytubefix | YouTube transcript extraction |

### Frontend
| Technology | Purpose |
|---|---|
| React 19 | UI framework |
| Vite 7 | Build tool & dev server |
| Tailwind CSS v4 | Utility-first styling |
| React Router v7 | Client-side routing |
| React Markdown | Markdown rendering |
| rehype-highlight | Code syntax highlighting |
| Lucide React | Icon library |

---

## 📸 How It Works

1. **Paste a YouTube URL** on the home page
2. The backend **extracts the transcript** using pytubefix
3. Transcript is **split into chunks** and stored in a ChromaDB vector store
4. **Ask a question** — the AI pipeline:
   - **Reformulates** vague queries using conversation history
   - **Retrieves** relevant chunks via similarity search
   - **Drafts** an answer with the LLM
   - A **judge** evaluates quality — if insufficient, triggers a **Tavily web search**
   - **Generates** a final structured response with follow-up suggestions
5. Response is **streamed live** via SSE with real-time status updates
6. Full conversation is **persisted to MySQL** for history

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `api_key` | Google Gemini API key ([Get one here](https://aistudio.google.com/apikey)) |
| `tavily_key` | Tavily Search API key ([Get one here](https://tavily.com)) |
| `SECRET_KEY` | JWT signing secret (random hex string) |
| `ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes (default: `60`) |
| `DB_URL` | MySQL connection string |

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

Built by [Pavan Kumar](https://github.com/Pavan-Kumar-45)

</div>