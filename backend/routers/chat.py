from fastapi import APIRouter, Depends, HTTPException, HTTPException, status
from requests import Session
from rpds import List
from backend import db
from backend.db import get_db
from backend.models import CreateChat, ReturnChat, UpdateName
from backend.routers.auth import get_current_user
from backend.schemas import Chat
from pytubefix import YouTube
from pytubefix.exceptions import VideoUnavailable, VideoPrivate
import requests



router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)
video_info = {}
def is_valid_youtube_url(url: str) -> bool:
    try:
        yt = YouTube(url)
        video_info[url] = {
            "title": yt.title,
            "author": yt.author,
            "thumbnail_url": yt.thumbnail_url
        }
        return True
    except VideoUnavailable:
        print(f"Error: {url} is unavailable.")
        return False
    except VideoPrivate:
        print(f"Error: {url} is a private video.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Network error or bot detection: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

 

@router.post("/create", response_model=ReturnChat, status_code=status.HTTP_201_CREATED)
def create_chat(chat: CreateChat, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_valid_youtube_url(chat.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL"
        )
    
    yt_info = video_info[chat.url]
    
    # Use video title as default name if not provided
    chat_name = chat.name if chat.name else yt_info["title"]
    
    new_chat = Chat(
        name=chat_name,
        url=chat.url,
        user_id=user.id,
        title=yt_info["title"],
        thumbnail_url=yt_info["thumbnail_url"]
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return ReturnChat(
        id=new_chat.id,
        name=new_chat.name,
        url=new_chat.url,
        title=yt_info["title"],
        author=yt_info["author"],
        thumbnail_url=yt_info["thumbnail_url"],
        created_at=new_chat.created_at,
        last_session=new_chat.last_session
    )

@router.get("/list", response_model=list[ReturnChat],status_code=status.HTTP_200_OK)
def list_chats(user=Depends(get_current_user), db: Session = Depends(get_db)):
    chats = db.query(Chat).filter(Chat.user_id == user.id).order_by(Chat.last_session.desc()).all()
    result = []
    for chat in chats:
        yt_info = video_info[chat.url]
        result.append(ReturnChat(
            id=chat.id,
            name=chat.name,
            url=chat.url,
            title=yt_info["title"],
            author=yt_info["author"],
            thumbnail_url=yt_info["thumbnail_url"],
            created_at=chat.created_at,
            last_session=chat.last_session
        ))
    return result 

@router.delete("/delete/{chat_id}", status_code=status.HTTP_200_OK)
def delete_chat(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    else:
        db.delete(chat)
        db.commit()
        return {"message": "Chat deleted successfully"} 
    
@router.get("/get/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def get_chat(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    yt_info = video_info[chat.url]
    return ReturnChat(
        id=chat.id,
        name=chat.name,
        url=chat.url,
        title=yt_info["title"],
        author=yt_info["author"],
        thumbnail_url=yt_info["thumbnail_url"],
        created_at=chat.created_at,
        last_session=chat.last_session
    )


@router.post("/{chat_id}/message")
async def send_message(chat_id: int, user_input: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Send a message and get AI response - uses the graph agent"""
    from backend.graph import get_chat_graph
    from backend.models import Output
    from langchain_core.messages import HumanMessage
    
    # Validate chat ownership
    chat_obj = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat_obj:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get the graph for this URL
    app = get_chat_graph(chat_id=chat_id, url=chat_obj.url)
    question = user_input.get("question") or user_input.get("message")
    
    config = {"configurable": {"thread_id": str(chat_id)}}
    inputs = {"messages": [HumanMessage(content=question)], "question": question}
    
    # Run the graph and get the final state
    final_state = app.invoke(inputs, config=config)
    messages = final_state.get('messages', [])
    
    if messages:
        response_content = messages[-1].content
        # Parse if it's JSON
        try:
            import json
            response_data = json.loads(response_content)
            # Add video title from stored info
            if chat_obj.url in video_info:
                response_data["title"] = video_info[chat_obj.url]["title"]
            return response_data
        except:
            return {"answer": response_content, "follow_up": []}
    
    return {"answer": "Sorry, I couldn't process that.", "follow_up": []}

@router.put("/update_name/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def update_chat_name(chat_id: int, new_name: UpdateName, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    chat.name = new_name.name
    db.commit()
    db.refresh(chat)
    yt_info = video_info[chat.url]
    return ReturnChat(
        id=chat.id,
        name=chat.name,
        url=chat.url,
        title=yt_info["title"],
        author=yt_info["author"],
        thumbnail_url=yt_info["thumbnail_url"],
        created_at=chat.created_at,
        last_session=chat.last_session
    )       