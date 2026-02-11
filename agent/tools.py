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
        query={"top_k": 5, "inputs": {"text": query}},
        fields=["title", "content", "topic"]
    )

    hits = results.get("result", {}).get("hits", [])
    if not hits:
        return "No relevant knowledge base documents found. Answer from your general knowledge."

    # Format the results as context for Claude
    context_parts = []
    for hit in hits:
        fields = hit.get("fields", {})
        score = hit.get("_score", 0)
        # Only include results with a reasonable similarity score
        if score < 0.5:
            continue
        context_parts.append(
            f"[{fields.get('title', 'Untitled')}] (relevance: {score:.2f})\n"
            f"{fields.get('content', '')}"
        )

    if not context_parts:
        return "No sufficiently relevant documents found. Answer from your general knowledge."

    return "Retrieved knowledge base context:\n\n" + "\n\n---\n\n".join(context_parts)


@tool
def read_form_data(project_id: str, section: str = "") -> str:
    """Read the user's current survey responses from Firestore.

    Use this when you need to understand what the user has already filled out
    in their cofounder agreement to give contextual advice.
    """
    if not db:
        return "[Firestore not connected — Firebase credentials not configured.]"

    doc_ref = db.collection("projects").document(project_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"No project found with ID: {project_id}"

    data = doc.to_dict()
    form_data = data.get("formData", {})

    if not form_data:
        return "The survey is empty — no form data has been filled out yet."

    filled_fields = {k: v for k, v in form_data.items() if v not in [None, "", [], {}]}

    if not filled_fields:
        return "The survey is empty — no form data has been filled out yet."

    summary_parts = []
    for field, value in filled_fields.items():
        display_name = field.replace("_", " ").title()
        summary_parts.append(f"- {display_name}: {value}")

    return f"Current survey responses ({len(filled_fields)} fields filled):\n\n" + "\n".join(summary_parts)


@tool
def check_completion(project_id: str) -> str:
    """Check survey completion progress and identify incomplete sections.

    Use this when the user asks about their progress or what's left to do.
    """
    if not db:
        return "[Firestore not connected — Firebase credentials not configured.]"

    doc_ref = db.collection("projects").document(project_id)
    doc = doc_ref.get()

    if not doc.exists:
        return f"No project found with ID: {project_id}"

    data = doc.to_dict()
    form_data = data.get("formData", {})
    filled_fields = {k: v for k, v in form_data.items() if v not in [None, "", [], {}]}

    return (
        f"Project has {len(filled_fields)} fields filled out of the total survey fields. "
        f"Project status: {data.get('status', 'unknown')}."
    )


# List of all tools available to the agent.
all_tools = [rag_search, read_form_data, check_completion]
