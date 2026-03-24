"""
Chat persistence — save and load conversations from Firestore.

Firestore structure:
  chats/{chatId}
    userId: "user-123"
    projectId: "project-456"
    createdAt: timestamp
    updatedAt: timestamp
    messages: [
      {role: "user", content: "...", timestamp: ...},
      {role: "assistant", content: "...", timestamp: ...}
    ]

Each chat has a unique UUID. userId and projectId are fields
for querying and security rules.
"""

import uuid
from datetime import datetime, timezone
from agent.services import db


def create_chat(user_id: str, project_id: str) -> str:
    """Create a new chat document. Returns the generated chat ID."""
    chat_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    if db:
        db.collection("chats").document(chat_id).set({
            "userId": user_id,
            "projectId": project_id,
            "messages": [],
            "createdAt": now,
            "updatedAt": now,
        })

    return chat_id


def load_chat(chat_id: str) -> dict:
    """
    Load a chat by its ID.
    Returns the full document dict, or None if not found.
    """
    if not db:
        return None

    doc = db.collection("chats").document(chat_id).get()
    if not doc.exists:
        return None

    return doc.to_dict()


def load_user_chats(user_id: str, project_id: str = None) -> list:
    """
    Load all chats for a user, optionally filtered by project.
    Returns a list of chat summaries (no message content).
    """
    if not db:
        return []

    query = db.collection("chats").where("userId", "==", user_id)
    if project_id:
        query = query.where("projectId", "==", project_id)

    results = []
    for doc in query.stream():
        data = doc.to_dict()
        results.append({
            "chatId": doc.id,
            "projectId": data.get("projectId"),
            "createdAt": data.get("createdAt"),
            "updatedAt": data.get("updatedAt"),
            "messageCount": len(data.get("messages", [])),
        })

    return results


def save_chat(chat_id: str, messages: list):
    """Save messages to an existing chat document."""
    if not db:
        return

    now = datetime.now(timezone.utc)

    for msg in messages:
        if "timestamp" not in msg:
            msg["timestamp"] = now.isoformat()

    db.collection("chats").document(chat_id).update({
        "messages": messages,
        "updatedAt": now,
    })


def delete_chat(chat_id: str):
    """Permanently delete a chat document from Firestore."""
    if not db:
        return

    db.collection("chats").document(chat_id).delete()


def load_project(project_id: str) -> dict:
    """Load a project document from Firestore. Returns the full dict, or {} if not found."""
    if not db:
        return {}

    doc = db.collection("projects").document(project_id).get()
    if not doc.exists:
        return {}

    return doc.to_dict()
