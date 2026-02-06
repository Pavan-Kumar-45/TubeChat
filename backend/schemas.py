from backend.db import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone


class User(Base):
    """SQLAlchemy model for user accounts."""

    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    """SQLAlchemy model for chat sessions linked to YouTube videos."""

    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    url = Column(String(500), nullable=False)

    title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    thumbnail_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_session = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """SQLAlchemy model for individual chat messages."""

    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)
    role = Column(String(10), nullable=False)   # 'user' or 'ai'
    content = Column(Text, nullable=False)
    follow_up = Column(Text, nullable=True)     # JSON string of follow-up questions
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    chat = relationship("Chat", back_populates="messages")