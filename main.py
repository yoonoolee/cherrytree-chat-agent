"""
Cherrytree Cofounder Advisor — FastAPI Server

This is the entry point. It creates an HTTP server with two endpoints:
  - GET  /       → serves the test chat UI
  - GET  /health → returns {"status": "ok"} for health checks
  - POST /chat   → accepts a user message, runs the LangGraph agent, returns the response

Local:  uvicorn main:app --reload --port 8000
Prod:   Deployed on Google Cloud Run
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from langsmith import Client as LangSmithClient

# Load environment variables from .env file (API keys, etc.)
# override=True ensures .env values take precedence over any existing env vars
load_dotenv(override=True)

# Import the agent runner and chat store (must come after load_dotenv so the API key is available)
from agent.graph import run_agent
from agent.chat_store import load_user_chats, load_chat, delete_chat

# Resolve the project root directory for serving static files
BASE_DIR = Path(__file__).resolve().parent

# Create the FastAPI app
app = FastAPI(
    title="Cherrytree Cofounder Advisor",
    version="0.1.0",
)

# CORS middleware — controls which domains can call this API.
# Without this, the browser blocks requests from different origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "https://cherrytree.app",  # Production
        "https://my.cherrytree.app",  # Production alt
        "https://cherrytree-cofounder-agree-dev.web.app",  # Firebase dev
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# --- Request/Response schemas ---
# Pydantic validates incoming JSON and outgoing responses automatically.

class ChatRequest(BaseModel):
    message: str                        # The user's current message
    user_id: str                        # Who is chatting (each user has private chat)
    project_id: str                     # Which project this chat belongs to
    chat_id: str = ""                   # Which chat (empty = start a new chat)
    conversation_history: list = []     # All previous messages (for multi-turn context)
    current_section: str = ""           # Which survey section the user is on
    completion_percent: int = 0         # How far along the survey is (0-100)


class ChatResponse(BaseModel):
    response: str                       # The agent's response text
    conversation_history: list          # Updated history including the new exchange
    chat_id: str = ""                   # The chat ID (returned so frontend can track it)
    run_id: str = ""                    # LangSmith trace ID (for attaching feedback)


class FeedbackRequest(BaseModel):
    run_id: str                         # Which trace to attach feedback to
    score: int                          # 1 = thumbs up, 0 = thumbs down


# --- Routes ---

@app.get("/")
def index():
    """Serve the test chat UI (static/index.html)."""
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    """Health check — used by Cloud Run and monitoring to verify the service is alive."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Flow:
    1. Receives the user's message + conversation history + survey context
    2. Passes everything to the LangGraph agent (agent/graph.py)
    3. Agent reasons, optionally calls tools, generates a response
    4. Returns the response + updated conversation history
    """
    try:
        result = await run_agent(
            message=request.message,
            user_id=request.user_id,
            project_id=request.project_id,
            chat_id=request.chat_id or None,
            conversation_history=request.conversation_history,
            current_section=request.current_section,
            completion_percent=request.completion_percent,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats/{user_id}")
def get_user_chats(user_id: str, project_id: str = ""):
    """List all chats for a user, optionally filtered by project."""
    chats = load_user_chats(user_id, project_id or None)
    return {"chats": chats}


@app.get("/chat/{chat_id}")
def get_chat(chat_id: str):
    """Get a single chat with its full message history."""
    chat = load_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback (thumbs up/down) on an agent response.
    Attaches the rating to the LangSmith trace so you can filter
    by feedback in the dashboard.
    """
    try:
        client = LangSmithClient()
        client.create_feedback(
            run_id=request.run_id,
            key="user-rating",
            score=request.score,
            comment="thumbs up" if request.score == 1 else "thumbs down",
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chats/{chat_id}")
def remove_chat(chat_id: str):
    """Permanently delete a chat from Firestore."""
    delete_chat(chat_id)
    return {"status": "deleted"}
