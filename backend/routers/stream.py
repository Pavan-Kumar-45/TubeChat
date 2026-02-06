from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage
from backend.db import get_db
from backend.schemas import Chat, Message
from backend.routers.auth import get_current_user
from backend.graph import get_chat_graph
from backend.models import ChatInput
from backend.agents import build_chat_context, BUFFER_SIZE
from datetime import datetime, timezone
import json

router = APIRouter(prefix="/stream", tags=["stream"])

# Per-chat running summary cache: { chat_id: str }
_summary_cache: dict[int, str] = {}


def _load_chat_history(db: Session, chat_id: int) -> tuple[list[dict], str]:
    """Load chat messages from the database and apply the summary buffer.

    Keeps only the most recent BUFFER_SIZE messages in full; older messages
    are condensed into a running summary.

    Args:
        db: Active database session.
        chat_id: ID of the chat to load history for.

    Returns:
        Tuple of (recent_history, summary_text).
    """
    msgs = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    
    history = [{"role": m.role, "content": m.content} for m in msgs]
    existing_summary = _summary_cache.get(chat_id, "")
    
    # Apply buffer: summarize overflow, keep recent
    recent, summary = build_chat_context(history, existing_summary)
    
    # Cache the new summary
    if summary != existing_summary:
        _summary_cache[chat_id] = summary
    
    return recent, summary

@router.post("/{chat_id}")
async def stream_chat(
    chat_id: int, 
    user_input: ChatInput, 
    user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Stream an AI response for a chat question via Server-Sent Events.

    Saves the user message to DB before streaming, runs the LangGraph
    pipeline node-by-node emitting status updates, and saves the AI
    response to DB after completion.

    Args:
        chat_id: ID of the chat session.
        user_input: Request body containing the question.
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        StreamingResponse with SSE events (status, result, error).
    """
    # 1. Validate ownership and get URL
    chat_obj = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat_obj:
        raise HTTPException(status_code=404, detail="Chat not found")

    # 2. Get the persistent Graph for this chat ID
    app = get_chat_graph(chat_id=chat_id, url=chat_obj.url)

    # 3. Define the generator for StreamingResponse
    async def event_generator():
        query = user_input.question
        
        config = {"configurable": {"thread_id": str(chat_id)}}
        
        # Load chat history with summary buffer
        chat_history, summary = _load_chat_history(db, chat_id)
        
        inputs = {
            "messages": [HumanMessage(content=query)],
            "question": query,
            "chat_history": chat_history,
            "summary": summary,
        }

        try:
            # Save user message to DB
            user_msg = Message(chat_id=chat_id, role="user", content=query)
            db.add(user_msg)
            db.commit()

            result_payload = None

            for event in app.stream(inputs, config=config):
                for node_name, state_update in event.items():
                    if node_name == "REFORMULATE":
                         yield f"data: {json.dumps({'type': 'status', 'msg': 'Understanding query...'})}\n\n"
                    elif node_name == "RETRIEVER":
                         yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching video...'})}\n\n"
                    elif node_name == "AGENT":
                         yield f"data: {json.dumps({'type': 'status', 'msg': 'Analyzing...'})}\n\n"
                    elif node_name == "JUDGE":
                        is_good = state_update.get('is_good', False)
                        status_msg = "Verified ✓" if is_good else "Refining answer..."
                        yield f"data: {json.dumps({'type': 'status', 'msg': status_msg})}\n\n"
                    elif node_name == "SEARCH_TAVILY":
                         yield f"data: {json.dumps({'type': 'status', 'msg': 'Searching the web...'})}\n\n"
                    elif node_name == "FINAL_AGENT":
                         yield f"data: {json.dumps({'type': 'status', 'msg': 'Finalizing...'})}\n\n"
                    elif node_name == "GENERATE_ANSWER":
                        messages = state_update.get('messages')
                        if messages:
                            final_json_str = messages[-1].content
                            result_payload = json.loads(final_json_str)
                            yield f"data: {json.dumps({'type': 'result', 'payload': result_payload})}\n\n"

            # Save AI message to DB
            if result_payload:
                ai_msg = Message(
                    chat_id=chat_id,
                    role="ai",
                    content=result_payload.get("answer", ""),
                    follow_up=json.dumps(result_payload.get("follow_up", []))
                )
                db.add(ai_msg)
                chat_obj.last_session = datetime.now(timezone.utc)
                db.commit()
                            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")