"""
Knowledge base ingestion script.

Reads JSONL files from knowledge/documents/, embeds them, and uploads to Pinecone.

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python knowledge/ingest.py

Run this whenever you add or update knowledge base documents.
"""

import json
import os
import glob
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

# Connect to Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("cherrytree-knowledge")

# Directory containing knowledge base files
DOCS_DIR = os.path.join(os.path.dirname(__file__), "documents")


def load_documents():
    """Load all JSONL files from the documents directory."""
    documents = []
    for filepath in glob.glob(os.path.join(DOCS_DIR, "*.jsonl")):
        filename = os.path.basename(filepath)
        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    documents.append(doc)
                except json.JSONDecodeError:
                    print(f"  Skipping invalid JSON in {filename} line {line_num}")
        print(f"  Loaded {filename}")
    return documents


def ingest(documents):
    """Embed and upload documents to Pinecone."""
    # Build records for upsert — Pinecone generates embeddings from the "text" field
    # when using integrated embedding models
    records = []
    for doc in documents:
        # Combine title and content for better embedding
        text = f"{doc['title']}: {doc['content']}"
        # Fields are flat — Pinecone stores "text" for embedding,
        # everything else becomes searchable metadata
        records.append({
            "id": doc["id"],
            "text": text,
            "topic": doc.get("topic", ""),
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
        })

    # Upsert in batches of 50
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        # Use integrated embedding — Pinecone embeds the "text" field automatically
        index.upsert_records("cherrytree", batch)
        print(f"  Uploaded batch {i // batch_size + 1} ({len(batch)} records)")


def main():
    print("Loading documents...")
    documents = load_documents()
    print(f"Found {len(documents)} documents\n")

    if not documents:
        print("No documents found. Add JSONL files to knowledge/documents/")
        return

    print("Ingesting into Pinecone...")
    ingest(documents)
    print(f"\nDone. {len(documents)} documents indexed in Pinecone.")

    # Verify
    stats = index.describe_index_stats()
    print(f"Index stats: {stats}")


if __name__ == "__main__":
    main()
