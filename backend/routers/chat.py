from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models import CreateChat, ReturnChat, UpdateName, ReturnMessage
from backend.routers.auth import get_current_user
from backend.schemas import Chat, Message
from pytubefix import YouTube
from pytubefix.exceptions import VideoUnavailable, VideoPrivate
import requests
import json


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

# In-memory cache so we don't re-fetch YouTube metadata within the same process
_video_info_cache: dict[str, dict] = {}


def get_video_info(url: str) -> dict:
    """Fetch YouTube video metadata, returning cached results when available.

    Args:
        url: YouTube video URL.

    Returns:
        Dict with 'title', 'author', and 'thumbnail_url' keys.
    """
    if url in _video_info_cache:
        return _video_info_cache[url]

    try:
        yt = YouTube(url)
        _video_info_cache[url] = {
            "title": yt.title,
            "author": yt.author,
            "thumbnail_url": yt.thumbnail_url,
        }
        return _video_info_cache[url]
    except Exception as e:
        print(f"Error fetching video info for {url}: {e}")
        return {
            "title": "Video Unavailable",
            "author": "Unknown",
            "thumbnail_url": "",
        }


def is_valid_youtube_url(url: str) -> bool:
    """Validate a YouTube URL by attempting to access the video.

    Also populates the video info cache on success.

    Args:
        url: YouTube video URL to validate.

    Returns:
        True if the video is accessible, False otherwise.
    """
    try:
        yt = YouTube(url)
        _video_info_cache[url] = {
            "title": yt.title,
            "author": yt.author,
            "thumbnail_url": yt.thumbnail_url,
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


def _chat_to_return(chat: Chat) -> ReturnChat:
    """Convert a Chat ORM object to a ReturnChat response model.

    Uses stored DB fields — never calls the YouTube API.

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

    Validates the URL, fetches video metadata, and persists the chat.

    Args:
        chat: Request body with YouTube URL and optional name.
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        The newly created chat as ReturnChat.

    Raises:
        HTTPException 400: If the YouTube URL is invalid or inaccessible.
    """
    if not is_valid_youtube_url(chat.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL",
        )

    yt_info = _video_info_cache[chat.url]
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
def list_chats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all chats for the authenticated user, ordered by last session.

    Uses stored DB fields — no external API calls, so this is fast.

    Args:
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        List of ReturnChat models.
    """
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == user.id)
        .order_by(Chat.last_session.desc())
        .all()
    )
    return [_chat_to_return(c) for c in chats]

@router.delete("/delete/{chat_id}", status_code=status.HTTP_200_OK)
def delete_chat(
    chat_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a chat and all its messages.

    Args:
        chat_id: ID of the chat to delete.
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        Success confirmation message.

    Raises:
        HTTPException 404: If chat not found or not owned by user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted successfully"}

    
@router.get("/get/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def get_chat(
    chat_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single chat by ID.

    Args:
        chat_id: ID of the chat.
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        ReturnChat model for the requested chat.

    Raises:
        HTTPException 404: If chat not found or not owned by user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    return _chat_to_return(chat)


@router.get("/{chat_id}/messages", response_model=list[ReturnMessage], status_code=status.HTTP_200_OK)
def get_messages(
    chat_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all messages for a chat, ordered chronologically.

    Args:
        chat_id: ID of the chat.
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        List of ReturnMessage models.

    Raises:
        HTTPException 404: If chat not found or not owned by user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    msgs = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    result = []
    for m in msgs:
        follow_up: list[str] = []
        if m.follow_up:
            try:
                follow_up = json.loads(m.follow_up)
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(
            ReturnMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                follow_up=follow_up,
                created_at=m.created_at,
            )
        )
    return result


@router.put("/update_name/{chat_id}", response_model=ReturnChat, status_code=status.HTTP_200_OK)
def update_chat_name(
    chat_id: int,
    new_name: UpdateName,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a chat.

    Args:
        chat_id: ID of the chat to rename.
        new_name: Request body with the new name.
        user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        Updated ReturnChat model.

    Raises:
        HTTPException 404: If chat not found or not owned by user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    chat.name = new_name.name
    db.commit()
    db.refresh(chat)
    return _chat_to_return(chat)