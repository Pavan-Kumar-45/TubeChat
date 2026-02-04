from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- Auth Schemas ---
class Login(BaseModel):
    username: str
    password: str

class Register(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: int
    username: str

# --- Chat Management Schemas ---
class CreateChat(BaseModel):
    url: str = Field(..., description="YouTube video URL")
    name: str = Field(None, description="Optional name")

class ReturnChat(BaseModel):
    id: int
    name: str
    url: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    author: Optional[str] = None
    created_at: datetime
    last_session: datetime

    class Config:
        from_attributes = True

class UpdateName(BaseModel):
    name: str

# --- Streaming/Chat Interaction Schemas ---
class ChatInput(BaseModel):
    question: str

# --- Response Schemas ---
class JudgeEval(BaseModel):
  is_good: bool = Field(description="True if the answer is accurate and sufficient, False if it needs improvement")
  feedback: str = Field(description="Specific instructions on what to fix")

class Output(BaseModel):
  title : str = Field("Title of the Youtube video")
  question : str = Field("User query, dont change the user query keep it as it is")
  answer : str = Field("Answer of the user query")
  follow_up : list[str] = Field("3-4 follow up questions")