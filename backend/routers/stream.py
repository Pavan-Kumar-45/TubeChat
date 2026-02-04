from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage
from backend.db import get_db
from backend.schemas import Chat
from backend.routers.auth import get_current_user
from backend.graph import get_chat_graph
from backend.models import ChatInput
import json

router = APIRouter(prefix="/stream", tags=["stream"])

@router.post("/{chat_id}")
async def stream_chat(
    chat_id: int, 
    user_input: ChatInput, 
    user=Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # 1. Validate ownership and get URL
    chat_obj = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat_obj:
        raise HTTPException(status_code=404, detail="Chat not found")

    # 2. Get the persistent Graph for this chat ID
    app = get_chat_graph(chat_id=chat_id, url=chat_obj.url)

    # 3. Define the generator for StreamingResponse
    async def event_generator():
        query = user_input.question
        
        # We use the chat_id as the thread_id for LangGraph memory
        config = {"configurable": {"thread_id": str(chat_id)}}
        inputs = {"messages": [HumanMessage(content=query)], "question": query}

        # Stream events from LangGraph
        try:
            # We iterate over the graph updates
            for event in app.stream(inputs, config=config):
                
                # Check which node just finished
                for node_name, state_update in event.items():
                    
                    # Send status updates to frontend
                    if node_name == "RETRIEVER":
                         yield f"data: {json.dumps({'type': 'status', 'msg': 'Thinking...'})}\n\n"
                    elif node_name == "JUDGE":
                        is_good = state_update.get('is_good', False)
                        status_msg = "Answer Validated" if is_good else "Refining Answer..."
                        yield f"data: {json.dumps({'type': 'status', 'msg': status_msg})}\n\n"
                    
                    # Send the Final Answer
                    elif node_name == "GENERATE_ANSWER":
                        messages = state_update.get('messages')
                        if messages:
                            # Parse the JSON string from the AI output
                            final_json_str = messages[-1].content
                            yield f"data: {json.dumps({'type': 'result', 'payload': json.loads(final_json_str)})}\n\n"
                            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'msg': str(e)})}\n\n"

    # 4. Return the Streaming Response (Server-Sent Events)
    return StreamingResponse(event_generator(), media_type="text/event-stream")