from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from backend.agents import (
    AgentState, create_retriever_tool, agent, 
    judge, search_tavily, final_agent, 
    generate_answer, router, reformulate_query
)

# GLOBAL CACHE: Stores the compiled app for each chat_id
# Format: { chat_id: (compiled_graph_app, url) }
active_graphs = {}

def get_chat_graph(chat_id: int, url: str):
    """Return an existing compiled graph for a chat, or create a new one.

    Caches compiled LangGraph workflows per chat_id so that in-memory
    checkpointer state (conversation memory) is preserved across requests.

    Args:
        chat_id: Unique identifier for the chat session.
        url: YouTube video URL (used to build the retriever on first call).

    Returns:
        A compiled LangGraph application instance.
    """
    if chat_id in active_graphs:
        return active_graphs[chat_id][0]

    # Create new components for this specific URL
    retriever_tool = create_retriever_tool(url)
    
    workflow = StateGraph(AgentState)
    workflow.add_node("REFORMULATE", reformulate_query)
    workflow.add_node("RETRIEVER", retriever_tool)
    workflow.add_node("AGENT", agent)
    workflow.add_node("JUDGE", judge)
    workflow.add_node("SEARCH_TAVILY", search_tavily)
    workflow.add_node("FINAL_AGENT", final_agent)
    workflow.add_node("GENERATE_ANSWER", generate_answer)

    workflow.add_edge(START, "REFORMULATE")
    workflow.add_edge("REFORMULATE", "RETRIEVER")
    workflow.add_edge("RETRIEVER", "AGENT")
    workflow.add_edge("AGENT", "JUDGE")
    
    workflow.add_conditional_edges(
        "JUDGE",
        router,
        {"GENERATE_ANSWER": "GENERATE_ANSWER", "SEARCH_TAVILY": "SEARCH_TAVILY"}
    )
    
    workflow.add_edge("SEARCH_TAVILY", "FINAL_AGENT")
    workflow.add_edge("FINAL_AGENT", "GENERATE_ANSWER")
    workflow.add_edge("GENERATE_ANSWER", END)

    app = workflow.compile(checkpointer=InMemorySaver())
    
    # Cache it
    active_graphs[chat_id] = (app, url)
    return app