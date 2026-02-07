from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import CreateChat, ReturnChat, UpdateName, ReturnMessage
from backend.routers.auth import get_current_user
from backend.schemas import Chat, Message
import yt_dlp
import requests
import json
import re

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

# In-memory cache
_video_info_cache: dict[str, dict] = {}

def get_video_id(url: str) -> str | None:
    """
    Robust Regex to extract 11-char Video ID from ANY YouTube URL.
    Supports: shorts, live, embed, youtu.be, standard watch?v=
    """
    # This regex looks for 11 chars that follow: v=, /, embed/, be/, shorts/, or live/
    pattern = r'(?:v=|\/|embed\/|youtu\.be\/|shorts\/|live\/)([0-9A-Za-z_-]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def fetch_metadata_piped(video_id: str) -> dict | None:
    """Fetch metadata from Piped API (Bypasses IP blocks)."""
    try:
        response = requests.get(f"https://pipedapi.kavin.rocks/streams/{video_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", "YouTube Video"),
                "author": data.get("uploader", "Unknown"),
                "thumbnail_url": data.get("thumbnailUrl", "")
            }
    except Exception:
        pass
    return None

def get_yt_metadata(url: str) -> dict | None:
    """Fetch metadata using yt-dlp (Standard method)."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title', 'YouTube Video'),
                "author": info.get('uploader', 'Unknown Author'),
                "thumbnail_url": info.get('thumbnail', ''),
            }
    except Exception:
        return None

def is_valid_youtube_url(url: str) -> bool:
    """
    Validate URL using a 'Waterfall' strategy:
    1. Cache -> 2. yt-dlp -> 3. Piped API -> 4. Manual Fallback
    """
    if url in _video_info_cache:
        return True

    # Attempt 1: Try yt-dlp first (Most accurate)
    metadata = get_yt_metadata(url)

    # Attempt 2: If yt-dlp failed, try Piped API (Requires Video ID)
    if not metadata:
        video_id = get_video_id(url)
        if video_id:
            print(f"🔄 yt-dlp failed, trying Piped API for {video_id}...")
            metadata = fetch_metadata_piped(video_id)
    
    # Attempt 3: If Piped failed, use Manual Fallback (Requires Video ID)
    if not metadata:
        video_id = get_video_id(url) or get_video_id(url) # Retry ID extraction
        if video_id:
            print(f"⚠️ Metadata fetch failed. Using manual fallback for {url}")
            metadata = {
                "title": "YouTube Video (Metadata Hidden)",
                "author": "Unknown",
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            }
    
    # Success? Save to cache.
    if metadata:
        _video_info_cache[url] = metadata
        return True
    
    # If we still have no metadata and no ID, it's truly invalid.
    return False

def _chat_to_return(chat: Chat) -> ReturnChat:
    return ReturnChat(
        id=chat.id,
        name=chat.name or chat.title or "Untitled",
        url=chat.url,
        title=chat.title,
        author=chat.author,
        thumbnail_url=chat.thumbnail_url,
        created_at=chat.created_at,
        last_session=chat.last_session,
    )

@router.post("/create", response_model=ReturnChat, status_code=status.HTTP_201_CREATED)
def create_chat(
    chat: CreateChat,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_valid_youtube_url(chat.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL",
        )

    yt_info = _video_info_cache.get(chat.url)
    chat_name = chat.name if chat.name else yt_info["title"]

    new_chat = Chat(
        name=chat_name,
        url=chat.url,
        user_id=user.id,
        title=yt_info["title"],
        author=yt_info["author"],
        thumbnail_url=yt_info["thumbnail_url"],
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return _chat_to_return(new_chat)

@router.get("/list", response_model=list[ReturnChat], status_code=status.HTTP_200_OK)
def list_chats(user=Depends(get_current_user), db: Session = Depends(get_db)):
    chats = db.query(Chat).filter(Chat.user_id == user.id).order_by(Chat.last_session.desc()).all()
    return [_chat_to_return(c) for c in chats]

@router.delete("/delete/{chat_id}", status_code=status.HTTP_200_OK)
def delete_chat(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted successfully"}

@router.get("/get/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def get_chat(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return _chat_to_return(chat)

@router.get("/{chat_id}/messages", response_model=list[ReturnMessage], status_code=status.HTTP_200_OK)
def get_messages(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    msgs = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
    result = []
    for m in msgs:
        follow_up = []
        if m.follow_up:
            try:
                follow_up = json.loads(m.follow_up)
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(ReturnMessage(id=m.id, role=m.role, content=m.content, follow_up=follow_up, created_at=m.created_at))
    return result

@router.put("/update_name/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def update_chat_name(chat_id: int, new_name: UpdateName, user=Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    chat.name = new_name.name
    db.commit()
    db.refresh(chat)
    return _chat_to_return(chat)