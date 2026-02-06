from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.db import get_db
from backend.schemas import User, Chat  # SQLAlchemy models
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile information.

    Args:
        current_user: Authenticated user (injected).

    Returns:
        Dict with id, username, and created_at.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at
    }


@router.get("/chats")
def get_user_chats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all chats belonging to the authenticated user.

    Args:
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        List of chat dicts with id, name, url, created_at, last_session.
    """
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.last_session.desc()).all()
    return [
        {
            "id": chat.id,
            "name": chat.name,
            "url": chat.url,
            "created_at": chat.created_at,
            "last_session": chat.last_session
        }
        for chat in chats
    ]


@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a chat owned by the authenticated user.

    Args:
        chat_id: ID of the chat to delete.
        current_user: Authenticated user (injected).
        db: Database session (injected).

    Returns:
        Success confirmation message.

    Raises:
        HTTPException 404: If chat not found or not owned by user.
    """
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    db.delete(chat)
    db.commit()
    return {"message": "Chat deleted successfully"}
