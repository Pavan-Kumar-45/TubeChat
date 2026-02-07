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
    """Extract the 11-character video ID from a YouTube URL.

    Supports standard watch URLs, shortened youtu.be links, embeds, and shorts.

    Args:
        url: Any YouTube video URL.

    Returns:
        The 11-character video ID string, or None if no ID could be extracted.
    """
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

def fetch_metadata_piped(video_id: str) -> dict | None:
    """Fetch video metadata from the Piped API (public YouTube proxy).

    Used as a fallback when yt-dlp is blocked due to server IP restrictions
    on platforms like Render or AWS.

    Args:
        video_id: The 11-character YouTube video ID.

    Returns:
        Dict with 'title', 'author', and 'thumbnail_url' keys on success,
        or None if the request fails.
    """
    try:
        
        response = requests.get(f"https://pipedapi.kavin.rocks/streams/{video_id}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", "YouTube Video"),
                "author": data.get("uploader", "Unknown"),
                "thumbnail_url": data.get("thumbnailUrl", "")
            }
    except Exception as e:
        print(f"⚠️ Piped API failed: {e}")
    return None

def get_yt_metadata(url: str) -> dict | None:
    """Fetch video metadata using yt-dlp.

    Primary metadata strategy. Uses flat extraction with no download
    for fast, lightweight lookups. May fail on servers with blocked IPs.

    Args:
        url: YouTube video URL.

    Returns:
        Dict with 'title', 'author', and 'thumbnail_url' keys on success,
        or None if yt-dlp fails (e.g. IP block, bot detection).
    """
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
    """Validate a YouTube URL and populate the metadata cache.

    Uses a multi-strategy approach:
        1. Check if the URL is already cached.
        2. Extract the video ID via regex (rejects non-YouTube URLs).
        3. Try yt-dlp for metadata.
        4. Fall back to the Piped public API.
        5. Use a generic fallback with the thumbnail from img.youtube.com.

    The URL is only rejected if no valid video ID can be extracted.
    Metadata fetch failures never cause rejection.

    Args:
        url: The YouTube URL to validate.

    Returns:
        True if the URL contains a valid YouTube video ID, False otherwise.
    """
    if url in _video_info_cache:
        return True

    video_id = get_video_id(url)
    if not video_id:
        return False

    # Strategy 1: yt-dlp
    metadata = get_yt_metadata(url)
    
    # Strategy 2: Piped API (If yt-dlp failed)
    if not metadata:
        print(f"🔄 Switching to Piped API for {video_id}...")
        metadata = fetch_metadata_piped(video_id)

    # Strategy 3: Manual Fallback
    if not metadata:
        print(f"⚠️ All metadata fetches failed for {url}. Using generic fallback.")
        metadata = {
            "title": "YouTube Video (Metadata Hidden)",
            "author": "Unknown",
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        }

    _video_info_cache[url] = metadata
    return True

def _chat_to_return(chat: Chat) -> ReturnChat:
    """Convert a Chat ORM object to a ReturnChat response model.

    Uses stored DB fields only — never calls any external API.

    Args:
        chat: SQLAlchemy Chat instance.

    Returns:
        Populated ReturnChat pydantic model.
    """
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
    """Create a new chat session for a YouTube video.

    Validates the URL, fetches video metadata (with fallback), and persists
    the chat to the database.

    Args:
        chat: Request body with YouTube URL and optional name.
        user: Authenticated user (injected via dependency).
        db: Database session (injected via dependency).

    Returns:
        The newly created chat as a ReturnChat model.

    Raises:
        HTTPException 400: If the URL is not a valid YouTube link.
    """
    # This validates AND populates the cache
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
    """List all chats for the authenticated user, ordered by most recent session.

    Args:
        user: Authenticated user (injected via dependency).
        db: Database session (injected via dependency).

    Returns:
        List of ReturnChat models.
    """
    chats = db.query(Chat).filter(Chat.user_id == user.id).order_by(Chat.last_session.desc()).all()
    return [_chat_to_return(c) for c in chats]

@router.delete("/delete/{chat_id}", status_code=status.HTTP_200_OK)
def delete_chat(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a chat and all its associated messages.

    Args:
        chat_id: ID of the chat to delete.
        user: Authenticated user (injected via dependency).
        db: Database session (injected via dependency).

    Returns:
        Success confirmation dict.

    Raises:
        HTTPException 404: If the chat is not found or not owned by the user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted successfully"}

@router.get("/get/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def get_chat(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single chat by ID.

    Args:
        chat_id: ID of the chat to retrieve.
        user: Authenticated user (injected via dependency).
        db: Database session (injected via dependency).

    Returns:
        ReturnChat model for the requested chat.

    Raises:
        HTTPException 404: If the chat is not found or not owned by the user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return _chat_to_return(chat)

@router.get("/{chat_id}/messages", response_model=list[ReturnMessage], status_code=status.HTTP_200_OK)
def get_messages(chat_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all messages for a chat, ordered chronologically.

    Args:
        chat_id: ID of the chat whose messages to retrieve.
        user: Authenticated user (injected via dependency).
        db: Database session (injected via dependency).

    Returns:
        List of ReturnMessage models with parsed follow-up suggestions.

    Raises:
        HTTPException 404: If the chat is not found or not owned by the user.
    """
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
    """Rename a chat.

    Args:
        chat_id: ID of the chat to rename.
        new_name: Request body containing the new name.
        user: Authenticated user (injected via dependency).
        db: Database session (injected via dependency).

    Returns:
        Updated ReturnChat model.

    Raises:
        HTTPException 404: If the chat is not found or not owned by the user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    chat.name = new_name.name
    db.commit()
    db.refresh(chat)
    return _chat_to_return(chat)