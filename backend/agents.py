from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import YoutubeLoader
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from typing import TypedDict, Annotated, Sequence
from operator import add as add_messages
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from datetime import datetime
from backend.models import JudgeEval, Output
import os

load_dotenv()

api_key = os.getenv('api_key')
tavily_key = os.getenv('tavily_key')

llm = ChatGoogleGenerativeAI(
    api_key=api_key,
    model="gemini-2.5-flash-lite"
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


def get_vector_store(url: str) -> Chroma:
    """Get or create a Chroma vector store for a YouTube video transcript.

    Loads the transcript, splits it into chunks, embeds them, and caches
    the resulting vector store. Evicts the oldest entry when the cache is full.

    Args:
        url: YouTube video URL.

    Returns:
        A Chroma vector store instance.

    Raises:
        ValueError: If no transcript is available for the video.
    """
    if url in _vector_store_cache:
        print(f"[CACHE HIT] Using cached vector store for {url}")
        return _vector_store_cache[url]
    
    print(f"[LOADING] Fetching transcript for {url}...")
    try:
        loader = YoutubeLoader.from_youtube_url(url, add_video_info=False, language=["en", "en-US", "en-GB"])
        transcript = loader.load()
        print(f"[LOADED] Got {len(transcript)} document(s)")
    except Exception as e:
        print(f"[ERROR] Failed to load transcript: {e}")
        raise
    
    if not transcript:
        raise ValueError("No transcript available for this video")
    
    # Evict oldest if cache is full
    _evict_oldest_vector()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""]
    )
    docs = splitter.split_documents(transcript)
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
    """Create a retriever node function bound to a specific YouTube video.

    Returns a callable that performs similarity search against the video's
    vector store and filters results by a relevance threshold.

    Args:
        url: YouTube video URL to build the retriever for.

    Returns:
        A function compatible with the LangGraph AgentState interface.
    """
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
    """Summarize overflow messages to keep the conversation context compact.

    Merges the new messages with an existing summary into a concise
    3-5 sentence factual summary using the LLM.

    Args:
        chat_history: List of message dicts ({role, content}) to summarize.
        existing_summary: Previously accumulated summary text.

    Returns:
        Updated summary string.
    """
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
    """
    If history exceeds buffer, summarize the overflow and return trimmed history + updated summary.
    Returns (trimmed_history, updated_summary).
    """
    if len(chat_history) <= BUFFER_SIZE:
        return chat_history, summary
    
    # Split: oldest messages → summarize, newest → keep in buffer
    overflow = chat_history[:len(chat_history) - BUFFER_SIZE]
    recent   = chat_history[len(chat_history) - BUFFER_SIZE:]
    
    new_summary = summarize_history(overflow, summary)
    return recent, new_summary


def reformulate_query(state: AgentState) -> AgentState:
    """Rewrite the user's query into a standalone, search-optimized question.

    Resolves pronouns and vague references using conversation history and
    summary context. Passes through unchanged if no history exists.

    Args:
        state: Current agent state with question, chat_history, and summary.

    Returns:
        State update with the reformulated_query field set.
    """
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
    """Route to the next node based on the judge's evaluation.

    Args:
        state: Current agent state with is_good flag.

    Returns:
        'GENERATE_ANSWER' if the draft is good, 'SEARCH_TAVILY' otherwise.
    """
    is_good = state.get("is_good", False)
    
    if is_good:
        return "GENERATE_ANSWER"
    else:
        return "SEARCH_TAVILY"


def search_tavily(state: AgentState) -> AgentState:
    """Perform a fallback web search using the Tavily API.

    Appends search results to the existing documents list so the
    final agent has additional context.

    Args:
        state: Current agent state with question and documents.

    Returns:
        State update with search results appended to documents.
    """
    query = state["question"]
    
    tavily_search = TavilySearch(tavily_api_key=tavily_key)
    result = tavily_search.invoke(query)
    
    content = str(result)
    return {"documents": state["documents"] + [content]}


def agent(state: AgentState) -> AgentState:
    """Draft an answer using retrieved documents and conversation history.

    Constructs a detailed prompt with transcript context, conversation
    summary, and recent messages, then invokes the LLM for a draft response.

    Args:
        state: Current agent state with question, documents, chat_history, summary.

    Returns:
        State update with the draft answer appended to messages.
    """
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
    """Evaluate the quality of the draft answer using structured LLM output.

    Determines whether the draft fully and accurately answers the question.
    If not, provides specific feedback for improvement.

    Args:
        state: Current agent state with question and draft answer in messages.

    Returns:
        State update with is_good flag and feedback string.
    """
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
    """Generate the final structured response with title, answer, and follow-ups.

    Formats the draft answer into well-structured markdown with a title,
    the original question, comprehensive answer, and follow-up suggestions.

    Args:
        state: Current agent state with question and draft answer in messages.

    Returns:
        State update with the structured Output JSON as a message.
    """
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
    """Draft a revised answer after Tavily fallback search results are available.

    Re-uses the agent function with the enriched document context.

    Args:
        state: Current agent state with enriched documents from Tavily.

    Returns:
        State update with the revised draft answer.
    """
    return agent(state)