from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from backend.agents import (
    AgentState, create_retriever_tool, agent, 
    judge, search_tavily, final_agent, 
    generate_answer, router
)

# GLOBAL CACHE: Stores the compiled app for each chat_id
# Format: { chat_id: compiled_graph_app }
active_graphs = {}

def get_chat_graph(chat_id: int, url: str):
    """
    Returns an existing graph for this chat_id if it exists (preserving memory),
    or creates a new one if it's the first time interacting.
    """
    if chat_id in active_graphs:
        return active_graphs[chat_id]

    # Create new components for this specific URL
    retriever_tool = create_retriever_tool(url)
    
    workflow = StateGraph(AgentState)
    workflow.add_node("RETRIEVER", retriever_tool)
    workflow.add_node("AGENT", agent)
    workflow.add_node("JUDGE", judge)
    workflow.add_node("SEARCH_TAVILY", search_tavily)
    workflow.add_node("FINAL_AGENT", final_agent)
    workflow.add_node("GENERATE_ANSWER", generate_answer)

    workflow.add_edge(START, "RETRIEVER")
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
    active_graphs[chat_id] = app
    return app