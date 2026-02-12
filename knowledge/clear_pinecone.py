"""Clear all vectors from Pinecone index."""
import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("cherrytree-knowledge")

print("Clearing Pinecone index...")
index.delete(delete_all=True, namespace="cherrytree")
print("Done! Index cleared.")

stats = index.describe_index_stats()
print(f"Index stats: {stats}")
