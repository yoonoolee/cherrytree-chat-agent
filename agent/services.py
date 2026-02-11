"""
Shared service connections — Pinecone and Firebase.

Initialized once when the app starts. Imported by tools.py and chat_store.py
so we don't create multiple connections.
"""

import os
from pinecone import Pinecone
import firebase_admin
from firebase_admin import credentials, firestore

# --- Pinecone ---
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
pinecone_index = pc.Index("cherrytree-knowledge")

# --- Firebase ---
_cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if _cred_path and not firebase_admin._apps:
    _cred = credentials.Certificate(_cred_path)
    firebase_admin.initialize_app(_cred, {
        "projectId": os.getenv("GOOGLE_CLOUD_PROJECT"),
    })

db = firestore.client() if firebase_admin._apps else None
