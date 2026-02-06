from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# --- Auth Schemas ---
class Login(BaseModel):
    """Request body for user login."""

    username: str
    password: str


class Register(BaseModel):
    """Request body for user registration."""

    username: str
    password: str


class Token(BaseModel):
    """JWT token response after successful authentication."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Decoded JWT token payload."""

    id: int
    username: str


# --- Chat Management Schemas ---
class CreateChat(BaseModel):
    """Request body for creating a new chat session."""

    url: str = Field(..., description="YouTube video URL")
    name: str = Field(None, description="Optional name")


class ReturnChat(BaseModel):
    """Response model for chat session details."""

    id: int
    name: Optional[str] = None
    url: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    author: Optional[str] = None
    created_at: datetime
    last_session: datetime

    class Config:
        from_attributes = True


class UpdateName(BaseModel):
    """Request body for renaming a chat."""

    name: str


# --- Streaming/Chat Interaction Schemas ---
class ChatInput(BaseModel):
    """Request body for sending a question to the AI pipeline."""

    question: str


class ReturnMessage(BaseModel):
    """Response model for a single chat message."""

    id: int
    role: str
    content: str
    follow_up: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


# --- Response Schemas ---
class JudgeEval(BaseModel):
    """Structured output from the judge node evaluating answer quality."""

    is_good: bool = Field(description="True if the answer is accurate and sufficient, False if it needs improvement")
    feedback: str = Field(description="Specific instructions on what to fix")


class Output(BaseModel):
    """Structured final output from the generate_answer node."""

    title: str = Field(description="Title of the YouTube video")
    question: str = Field(description="User query, kept as-is")
    answer: str = Field(description="Answer to the user query in markdown")
    follow_up: list[str] = Field(description="3-4 follow-up questions")