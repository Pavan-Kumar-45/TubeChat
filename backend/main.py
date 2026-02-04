from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db import engine, Base
from backend.routers import auth, user, chat, stream

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Youtube RAG API",
    description="An API that uses RAG to answer questions based on Youtube videos.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(stream.router)


@app.get("/")
def root():
    return {"message": "Welcome to Youtube RAG API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
