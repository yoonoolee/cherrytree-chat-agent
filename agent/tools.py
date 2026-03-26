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
    """Search the knowledge base for cofounder agreement guidance, legal concepts, and scenario advice.

    Use this for any question about equity splits, vesting, IP, decision-making, non-competes,
    cofounder conflict, or startup legal frameworks. Prefer searching over relying on general
    knowledge when the question is domain-specific — the knowledge base has curated guidance
    that is more reliable than general knowledge for these topics.
    """
    # Search Pinecone — the integrated embedding model converts the query to a vector
    # and finds the most similar documents
    results = pinecone_index.search(
        namespace="cherrytree",
        query={"top_k": 100, "inputs": {"text": query}},
        fields=["title", "content", "topic"]
    )

    hits = results.get("result", {}).get("hits", [])
    if not hits:
        return "No relevant knowledge base documents found. Answer from your general knowledge."

    # Filter by score. Domain-specific KB compresses scores into ~0.65–0.90 — 0.80 cuts
    # out weak matches while keeping genuinely relevant ones. Revisit with a reranker
    # or adjusted threshold once KB grows to 50-100+ docs.
    SCORE_THRESHOLD = 0.80
    hits = [h for h in hits if h.get("_score", 0) >= SCORE_THRESHOLD]
    if not hits:
        return "No sufficiently relevant knowledge base documents found. Answer from your general knowledge."

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
