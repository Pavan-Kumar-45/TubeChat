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
    model="gemini-2.5-flash"
)

embeddings = GoogleGenerativeAIEmbeddings(
    api_key=api_key,
    model="models/gemini-embedding-001"
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    question: str
    documents: list[str]
    search_needed: bool
    retries: int
    feedback: str
    is_good: bool


# Cache for vector stores
_vector_store_cache = {}


def get_vector_store(url: str) -> Chroma:
    """Get or create vector store for a YouTube URL"""
    if url in _vector_store_cache:
        return _vector_store_cache[url]
    
    loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
    transcript = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
        separators=["\n\n", "\n", " ", ""]
    )
    docs = splitter.split_documents(transcript)
    
    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=f"youtube_{hash(url)}"
    )
    
    _vector_store_cache[url] = vector_store
    return vector_store


def create_retriever_tool(url: str):
    """Create a retriever tool for a specific YouTube URL"""
    vector_store = get_vector_store(url)
    
    def retriever_tool(state: AgentState) -> AgentState:
        """Retrieves relevant documents from vector store"""
        query = state["messages"][-1].content
        
        results = vector_store.similarity_search_with_score(query, k=10)
        
        found_docs = []
        threshold = 0.65
        for doc, score in results:
            if score >= threshold:
                found_docs.append(doc.page_content)
        
        return {
            "question": query,
            "documents": found_docs
        }
    
    return retriever_tool


def router(state: AgentState) -> str:
    """Route based on judge evaluation"""
    is_good = state.get("is_good", False)
    
    if is_good:
        return "GENERATE_ANSWER"
    else:
        return "SEARCH_TAVILY"


def search_tavily(state: AgentState) -> AgentState:
    """Fallback search using Tavily"""
    query = state["question"]
    
    tavily_search = TavilySearch(api_key=tavily_key)
    result = tavily_search.invoke(query)
    
    content = str(result)
    return {"documents": state["documents"] + [content]}


def agent(state: AgentState) -> AgentState:
    """Draft answer based on retrieved documents"""
    query = state['question']
    docs = state['documents']
    context_docs = "\n\n".join(docs)
    now = datetime.now()
    
    prompt = f"""You are a helpful AI agent specialized in answering questions about YouTube videos.

User query: {query}
Current datetime: {now}
Context from video transcript: {context_docs}

Instructions:
1. Generate a detailed answer using the context provided.
2. Include specific examples from the transcript when relevant.
3. If the query is unrelated to the context, politely indicate that.
"""
    
    result = llm.invoke(prompt)
    return {"messages": [result]}


 



def judge(state: AgentState) -> AgentState:
    """Evaluate the draft answer quality"""
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
    """Generate final structured output"""
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

Format the answer in clean markdown with proper headings, bullet points, and paragraphs.
"""
    
    structured_llm = llm.with_structured_output(Output)
    result = structured_llm.invoke(prompt)
    
    return {
        "messages": [AIMessage(content=result.model_dump_json(indent=2))]
    }


def final_agent(state: AgentState) -> AgentState:
    """Draft final answer after fallback search"""
    return agent(state)