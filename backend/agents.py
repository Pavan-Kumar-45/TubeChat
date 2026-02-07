from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from datetime import datetime
from backend.models import JudgeEval, Output
import yt_dlp
import requests
import re
import os
import json

load_dotenv()

api_key = os.getenv('api_key')
tavily_key = os.getenv('tavily_key')

llm = ChatGoogleGenerativeAI(
    api_key=api_key,
    model="gemini-2.0-flash"
)

embeddings = GoogleGenerativeAIEmbeddings(
    api_key=api_key,
    model="models/gemini-embedding-001"
)


class AgentState(TypedDict):
    """State schema passed through every node in the LangGraph pipeline."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    question: str
    reformulated_query: str      # rewritten query for retriever
    documents: list[str]
    feedback: str
    is_good: bool
    chat_history: list[dict]     # [{role, content}, ...] recent messages
    summary: str                 # summary of older messages


# Cache for vector stores (URL -> Chroma)
_vector_store_cache: dict[str, Chroma] = {}
MAX_CACHED_VECTORS = 3  # Only keep N vector stores in memory at a time


def _evict_oldest_vector():
    """Remove the oldest cached vector store when cache is full."""
    if len(_vector_store_cache) >= MAX_CACHED_VECTORS:
        oldest_url = next(iter(_vector_store_cache))
        vs = _vector_store_cache.pop(oldest_url)
        try:
            vs.delete_collection()
        except Exception:
            pass
        print(f"[EVICT] Cleared vector store for {oldest_url}")


def release_vector_store(url: str):
    """Manually release a vector store from cache."""
    if url in _vector_store_cache:
        vs = _vector_store_cache.pop(url)
        try:
            vs.delete_collection()
        except Exception:
            pass
        print(f"[RELEASE] Cleared vector store for {url}")


def get_transcript_text(url: str) -> str:
    """
    Robust transcript fetcher using yt-dlp with Cookie support.
    Bypasses IP blocks by injecting cookies and extracting the transcript URL directly.
    """
    # 1. Locate cookies.txt
    # We check multiple possible locations to support both Windows (Local) and Linux (Render)
    possible_paths = [
        "backend/cookies.txt",  # Standard location from root
        "cookies.txt",          # Inside backend folder
        os.path.join(os.getcwd(), "backend", "cookies.txt"), # Absolute path
    ]
    
    cookie_file = None
    for path in possible_paths:
        if os.path.exists(path):
            cookie_file = path
            print(f"[COOKIES] Found cookies at: {path}")
            break
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'writesubtitles': True,      # Check for manual subs
        'writeautomaticsub': True,   # Check for auto-generated subs
        # We don't write files, we just want the info dict
    }

    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    else:
        print("⚠️ [COOKIES] Warning: cookies.txt not found! You may get blocked.")

    print(f"[TRANSCRIPT] Fetching metadata via yt-dlp for {url}...")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Extract Info
            info = ydl.extract_info(url, download=False)
            
            # 2. Look for subtitles (Manual > Automatic)
            subs = info.get('subtitles') or info.get('automatic_captions')
            if not subs:
                raise ValueError("No subtitles found for this video.")

            # 3. Find English track (en, en-US, etc.)
            lang = next((l for l in ['en', 'en-US', 'en-orig', 'en-GB'] if l in subs), None)
            if not lang:
                # Fallback: take the first available language
                lang = next(iter(subs))
                print(f"[TRANSCRIPT] English not found, falling back to: {lang}")

            # 4. Get the JSON3 format URL (easiest to parse)
            formats = subs[lang]
            json3_url = next((f['url'] for f in formats if f.get('ext') == 'json3'), None)
            
            if not json3_url:
                # Fallback: Try vtt if json3 isn't listed (rare)
                json3_url = next((f['url'] for f in formats if f.get('ext') == 'vtt'), None)
                if not json3_url:
                    raise ValueError("Could not find a parsable subtitle format.")

            # 5. Download the transcript data
            print(f"[TRANSCRIPT] Downloading subtitle data from: {json3_url[:50]}...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            r = requests.get(json3_url, headers=headers)
            r.raise_for_status()

            # 6. Parse JSON3
            # Structure: { events: [ { segs: [ { utf8: "text" } ] } ] }
            try:
                data = r.json()
                text_parts = []
                for event in data.get('events', []):
                    segs = event.get('segs', [])
                    for seg in segs:
                        if 'utf8' in seg:
                            text_parts.append(seg['utf8'])
                
                full_text = "".join(text_parts).replace('\n', ' ')
                # Basic cleanup
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                return full_text

            except Exception:
                # If json parse fails (maybe it was VTT?), return raw text
                return r.text

    except Exception as e:
        print(f"[TRANSCRIPT ERROR] {e}")
        raise ValueError(f"Failed to fetch transcript: {str(e)}")


def get_vector_store(url: str) -> Chroma:
    """Get or create a Chroma vector store for a YouTube video transcript.
    """
    if url in _vector_store_cache:
        print(f"[CACHE HIT] Using cached vector store for {url}")
        return _vector_store_cache[url]
    
    print(f"[LOADING] Fetching transcript for {url}...")
    try:
        # Use our custom robust fetcher instead of YoutubeLoader
        text_content = get_transcript_text(url)
        print(f"[LOADED] Got transcript length: {len(text_content)} chars")
        
        # Create a Document object
        transcript_docs = [Document(page_content=text_content, metadata={"source": url})]
        
    except Exception as e:
        print(f"[ERROR] Failed to load transcript: {e}")
        raise
    
    # Evict oldest if cache is full
    _evict_oldest_vector()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""]
    )
    docs = splitter.split_documents(transcript_docs)
    print(f"[SPLIT] Created {len(docs)} chunks")
    
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=f"youtube_{hash(url)}"
    )
    print(f"[DONE] Vector store created")
    
    _vector_store_cache[url] = vector_store
    return vector_store


def create_retriever_tool(url: str):
    """Create a retriever node function bound to a specific YouTube video."""
    vector_store = get_vector_store(url)
    
    def retriever_tool(state: AgentState) -> AgentState:
        """Retrieves relevant documents from vector store"""
        # Use the reformulated query for better retrieval
        query = state.get("reformulated_query") or state["question"]
        
        results = vector_store.similarity_search_with_score(query, k=10)
        
        found_docs = []
        threshold = 0.65
        for doc, score in results:
            if score >= threshold:
                found_docs.append(doc.page_content)
        
        return {
            "question": state["question"],   # keep original question
            "documents": found_docs
        }
    
    return retriever_tool


# ── Buffer / Summary constants ──
BUFFER_SIZE = 10         # keep last N messages as-is


def summarize_history(chat_history: list[dict], existing_summary: str) -> str:
    """Summarize overflow messages to keep the conversation context compact."""
    if not chat_history:
        return existing_summary
    
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content'][:300]}" for m in chat_history
    )
    
    prev_summary = f"Previous summary:\n{existing_summary}" if existing_summary else ""

    prompt = f"""Condense the following conversation into a brief factual summary (3-5 sentences).
Preserve key topics discussed, questions asked, and conclusions reached.

{prev_summary}

Conversation to summarize:
{history_text}

Summary:"""
    
    result = llm.invoke(prompt)
    return result.content.strip()


def build_chat_context(chat_history: list[dict], summary: str) -> tuple[list[dict], str]:
    if len(chat_history) <= BUFFER_SIZE:
        return chat_history, summary
    
    # Split: oldest messages → summarize, newest → keep in buffer
    overflow = chat_history[:len(chat_history) - BUFFER_SIZE]
    recent   = chat_history[len(chat_history) - BUFFER_SIZE:]
    
    new_summary = summarize_history(overflow, summary)
    return recent, new_summary


def reformulate_query(state: AgentState) -> AgentState:
    """Rewrite the user's query into a standalone, search-optimized question."""
    question = state["question"]
    chat_history = state.get("chat_history", [])
    summary = state.get("summary", "")
    
    # If no history, the query is already standalone
    if not chat_history and not summary:
        return {"reformulated_query": question}
    
    # Build context string
    ctx_parts = []
    if summary:
        ctx_parts.append(f"Conversation summary: {summary}")
    if chat_history:
        recent = "\n".join(
            f"{m['role'].upper()}: {m['content'][:200]}" for m in chat_history[-6:]
        )
        ctx_parts.append(f"Recent messages:\n{recent}")
    context = "\n\n".join(ctx_parts)
    
    prompt = f"""Given the conversation context below, rewrite the user's latest query into a
standalone, specific question that would work well as a search query for a video transcript database.

Rules:
- Resolve all pronouns (it, this, that, they) to their concrete referents.
- If the user says "explain about it" or "tell me more", figure out what "it" refers to from context.
- Keep the reformulated query concise (1-2 sentences max).
- Do NOT answer the question, just rewrite it.
- If the query is already clear and standalone, return it as-is.

{context}

User's latest query: {question}

Reformulated query:"""
    
    result = llm.invoke(prompt)
    reformulated = result.content.strip().strip('"').strip("'")
    print(f"[REFORMULATE] '{question}' → '{reformulated}'")
    
    return {"reformulated_query": reformulated}


def router(state: AgentState) -> str:
    is_good = state.get("is_good", False)
    
    if is_good:
        return "GENERATE_ANSWER"
    else:
        return "SEARCH_TAVILY"


def search_tavily(state: AgentState) -> AgentState:
    query = state["question"]
    
    tavily_search = TavilySearch(tavily_api_key=tavily_key)
    result = tavily_search.invoke(query)
    
    content = str(result)
    return {"documents": state["documents"] + [content]}


def agent(state: AgentState) -> AgentState:
    """Draft an answer using retrieved documents and conversation history."""
    query = state['question']
    docs = state['documents']
    context_docs = "\n\n".join(docs)
    now = datetime.now()
    chat_history = state.get('chat_history', [])
    summary = state.get('summary', '')
    
    # Build history context
    history_parts = []
    if summary:
        history_parts.append(f"Conversation summary so far:\n{summary}")
    if chat_history:
        recent = "\n".join(
            f"{m['role'].upper()}: {m['content'][:300]}" for m in chat_history[-6:]
        )
        history_parts.append(f"Recent conversation:\n{recent}")
    history_ctx = "\n\n".join(history_parts) if history_parts else "No prior conversation."
    
    prompt = f"""You are a helpful AI agent specialized in answering questions about YouTube videos.

User query: {query}
Current datetime: {now}
Context from video transcript: {context_docs}

{history_ctx}

Instructions:
1. Generate a detailed answer using the context provided.
2. Include specific examples from the transcript when relevant.
3. Use the conversation history for continuity — don't repeat what was already discussed.
4. If the query is unrelated to the context, politely indicate that.
"""
    
    result = llm.invoke(prompt)
    return {"messages": [result]}


def judge(state: AgentState) -> AgentState:
    query = state['question']
    draft_answer = state['messages'][-1]
    
    prompt = f"""You are a strict technical critic evaluating an AI's answer.

User query: {query}
Draft answer: {draft_answer}

Evaluate this answer:
- If it fully and accurately answers the question, set is_good to True.
- If it is vague, incomplete, or contains hallucinations, set is_good to False and provide specific feedback.
"""
    
    structured_llm = llm.with_structured_output(JudgeEval)
    result = structured_llm.invoke(prompt)
    
    return {
        "is_good": result.is_good,
        "feedback": result.feedback
    }


def generate_answer(state: AgentState) -> AgentState:
    question = state["question"]
    draft_answer = state["messages"][-1].content
    
    prompt = f"""You are a helpful assistant formatting a response about a YouTube video.

User Query: {question}
Draft Answer: {draft_answer}

Provide:
1. title: A brief title for this conversation (e.g., "Understanding Vibe Coding")
2. question: The user's original question (keep it as is)
3. answer: The comprehensive answer in well-formatted markdown
4. follow_up: Array of 3-4 relevant follow-up questions

Formatting rules for the answer field:
- Use ## for main section headings and ### for sub-sections (never # — it's too large).
- Use **bold** for key terms and concepts on their first mention.
- Use bullet lists (- ) for listing items; use numbered lists (1. ) only for sequential steps.
- Keep paragraphs short (2-4 sentences max). Add a blank line between paragraphs.
- Use > blockquotes sparingly for notable quotes from the video.
- Wrap any code or technical terms inline with backticks.
- If including code examples, use fenced code blocks with the language tag (```go, ```python, etc.).
- End with a brief one-line summary or takeaway.
- Do NOT start the answer with a heading that just repeats the question.
"""
    
    structured_llm = llm.with_structured_output(Output)
    result = structured_llm.invoke(prompt)
    
    return {
        "messages": [AIMessage(content=result.model_dump_json(indent=2))]
    }


def final_agent(state: AgentState) -> AgentState:
    return agent(state)