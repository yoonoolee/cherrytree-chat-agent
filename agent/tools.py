"""
Agent tools — actions the advisor can take.

Tools are functions that the LLM can decide to call during a conversation.
The @tool decorator registers them with LangChain so LangGraph can:
  1. Tell Claude about available tools (via the function schema)
  2. Execute the tool when Claude decides to call it
  3. Return the tool's output back to Claude so it can use the result

The docstring of each tool is critical — Claude reads it to decide WHEN to use the tool.
"""

from langchain_core.tools import tool
from agent.services import pinecone_index, db


@tool
def rag_search(query: str) -> str:
    """Search the knowledge base for relevant legal information and cofounder scenario guidance.

    Use this when the user asks about specific cofounder situations, legal concepts,
    equity frameworks, or needs scenario-based advice.
    """
    # Search Pinecone — the integrated embedding model converts the query to a vector
    # and finds the most similar documents
    results = pinecone_index.search(
        namespace="cherrytree",
        query={"top_k": 3, "inputs": {"text": query}},
        fields=["title", "content", "topic"]
    )

    hits = results.get("result", {}).get("hits", [])
    if not hits:
        return "No relevant knowledge base documents found. Answer from your general knowledge."

    # Format the results as context for Claude.
    # No score threshold — dense embeddings compress all scores into a narrow band (~0.6–0.85)
    # regardless of actual relevance, so any cutoff is arbitrary. Claude handles irrelevant
    # context gracefully. Revisit with a reranker once the knowledge base grows to 50-100+ docs.
    context_parts = []
    for hit in hits:
        fields = hit.get("fields", {})
        context_parts.append(
            f"[{fields.get('title', 'Untitled')}]\n"
            f"{fields.get('content', '')}"
        )

    return "Retrieved knowledge base context:\n\n" + "\n\n---\n\n".join(context_parts)


# List of all tools available to the agent.
all_tools = [rag_search]
