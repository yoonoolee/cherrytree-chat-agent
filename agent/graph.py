"""
LangGraph orchestrator — the main agent graph.

This is the brain of the system. It defines a graph with nodes and edges:

  START → [advisor] → (decision) → END
                ↓           ↑
             [tools] ───────┘

Flow:
  1. User message comes in → goes to the "advisor" node
  2. Advisor node sends messages to Claude, which reasons and either:
     a. Responds directly → graph ends, response is returned
     b. Decides to call a tool → goes to "tools" node
  3. Tools node executes the tool and returns the result
  4. Result goes back to "advisor" node (step 2) so Claude can use the tool output
  5. This loop continues until Claude responds without calling any tools

This is a ReAct (Reason + Act) pattern — the agent reasons about what to do,
takes an action (tool call), observes the result, then reasons again.
"""

import json
import uuid
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import all_tools
from agent.chat_store import create_chat, load_chat, save_chat, load_project
from prompts.advisor_prompt import build_system_prompt

# Load unique RAG topics once at startup from the knowledge base file.
# Passed into the system prompt so Claude knows what's searchable.
_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "documents" / "knowledge_base.jsonl"

def _load_rag_topics() -> list[str]:
    if not _KB_PATH.exists():
        return []
    topics = set()
    with open(_KB_PATH) as f:
        for line in f:
            try:
                topics.add(json.loads(line)["topic"])
            except (json.JSONDecodeError, KeyError):
                continue
    return sorted(topics)

RAG_TOPICS = _load_rag_topics()

# Initialize Claude Sonnet 4.5 with tool-calling enabled.
# bind_tools() tells Claude about the available tools so it can decide to call them.
# temperature=0.3 keeps responses focused (0=deterministic, 1=creative).
llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.3,
    max_tokens=1024,
).bind_tools(all_tools)


async def advisor_node(state: AgentState) -> dict:
    """
    Main advisor agent node.

    Takes the current state (conversation + context), builds the system prompt,
    sends everything to Claude, and returns Claude's response.

    Claude may respond with:
    - Plain text (a direct answer to the user)
    - Tool calls (requests to search knowledge base, read form data, etc.)
    """
    # Build system prompt with the user's current survey context
    system_prompt = build_system_prompt(
        current_section=state.get("current_section", ""),
        survey_context=state.get("survey_context", {}),
        rag_topics=RAG_TOPICS,
    )

    # Prepend system prompt to the conversation messages
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]

    # Call Claude — this is the actual LLM API call
    response = await llm.ainvoke(messages)

    # Return the response. LangGraph appends it to state["messages"] automatically
    # because of the Annotated[list, add_messages] in AgentState.
    return {"messages": [response], "response": response.content}


def should_use_tools(state: AgentState) -> str:
    """
    Routing function — decides where the graph goes after the advisor node.

    Checks if Claude's last response includes tool calls:
    - If yes → route to "tools" node (execute the tools)
    - If no  → route to END (return the response to the user)
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# --- Build the graph ---

# StateGraph manages the state (AgentState) as it flows through nodes
graph_builder = StateGraph(AgentState)

# Add nodes — each node is a function that receives state and returns updates
graph_builder.add_node("advisor", advisor_node)      # The LLM reasoning node
graph_builder.add_node("tools", ToolNode(all_tools))  # Executes tool calls automatically

# Add edges — define how control flows between nodes
graph_builder.add_edge(START, "advisor")  # Always start at the advisor

# Conditional edge: after advisor, check if tools are needed
graph_builder.add_conditional_edges(
    "advisor",
    should_use_tools,
    {"tools": "tools", END: END}
)

# After tools run, go back to advisor so Claude can use the tool results
graph_builder.add_edge("tools", "advisor")

# Compile the graph into a runnable object
graph = graph_builder.compile()


async def stream_agent(
    message: str,
    user_id: str,
    project_id: str,
    chat_id: str = None,
    conversation_history: list = None,
    current_section: str = "",
):
    """
    Streaming entry point called by main.py's /chat/stream endpoint.

    Yields dicts:
      {"type": "token", "content": "..."}  — one per streamed text token
      {"type": "done",  "chat_id": "...", "run_id": "...", "conversation_history": [...]}

    Only streams tokens from the advisor node (not tool calls or tool results).
    Chat history is saved to Firestore at the end, same as run_agent.
    """
    if not chat_id:
        chat_id = create_chat(user_id, project_id)

    if not conversation_history:
        chat_doc = load_chat(chat_id)
        conversation_history = chat_doc.get("messages", []) if chat_doc else []

    # Fetch latest project data from Firestore on every message so the agent
    # always has the current survey state (user fills out survey between messages)
    project_doc = load_project(project_id)
    survey_context = project_doc.get("surveyData", {})

    messages = []
    for msg in (conversation_history or []):
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    run_id = str(uuid.uuid4())
    full_response = ""

    async for event in graph.astream_events(
        {
            "messages": messages,
            "project_id": project_id,
            "current_section": current_section,
            "survey_context": survey_context,
            "response": "",
        },
        config={"run_id": run_id},
        version="v2",
    ):
        # Only yield text tokens from the advisor node — skip tool call/result nodes
        if (
            event["event"] == "on_chat_model_stream"
            and event.get("metadata", {}).get("langgraph_node") == "advisor"
        ):
            chunk = event["data"]["chunk"]
            # Anthropic returns content as a list of blocks: [{"type": "text", "text": "..."}]
            if isinstance(chunk.content, list):
                for block in chunk.content:
                    text = block.get("text", "") if isinstance(block, dict) else ""
                    if text:
                        full_response += text
                        yield {"type": "token", "content": text}

    updated_history = list(conversation_history or [])
    updated_history.append({"role": "user", "content": message})
    updated_history.append({"role": "assistant", "content": full_response})
    save_chat(chat_id, updated_history)

    yield {
        "type": "done",
        "chat_id": chat_id,
        "run_id": run_id,
        "conversation_history": updated_history,
    }


async def run_agent(
    message: str,
    user_id: str,
    project_id: str,
    chat_id: str = None,
    conversation_history: list = None,
    current_section: str = "",
) -> dict:
    """
    Entry point called by main.py's /chat endpoint.

    Steps:
    1. If no chat_id, create a new chat in Firestore
    2. Load existing messages from Firestore if no history sent
    3. Run the LangGraph graph (which calls Claude, possibly uses tools, loops)
    4. Save updated messages and return the response
    """

    # If no chat_id provided, this is a new conversation — create one
    if not chat_id:
        chat_id = create_chat(user_id, project_id)

    # If no conversation history was sent by the frontend,
    # try loading it from Firestore (persisted from a previous session)
    if not conversation_history:
        chat_doc = load_chat(chat_id)
        conversation_history = chat_doc.get("messages", []) if chat_doc else []

    # Fetch latest project data from Firestore on every message so the agent
    # always has the current survey state (user fills out survey between messages)
    project_doc = load_project(project_id)
    survey_context = project_doc.get("surveyData", {})

    # Rebuild messages from conversation history
    messages = []
    for msg in (conversation_history or []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add the new user message
    messages.append({"role": "user", "content": message})

    # Generate a unique run ID for LangSmith tracing — this lets us attach
    # user feedback (thumbs up/down) to the exact trace later
    run_id = str(uuid.uuid4())

    # Run the graph — this triggers the full advisor → tools → advisor loop
    result = await graph.ainvoke(
        {
            "messages": messages,
            "project_id": project_id,
            "current_section": current_section,
            "survey_context": survey_context,
            "response": "",
        },
        config={"run_id": run_id},
    )

    # Extract the final response text from the graph's state
    response_text = result["response"]

    # Build updated conversation history
    updated_history = list(conversation_history or [])
    updated_history.append({"role": "user", "content": message})
    updated_history.append({"role": "assistant", "content": response_text})

    # Save the updated conversation to Firestore
    save_chat(chat_id, updated_history)

    return {
        "response": response_text,
        "conversation_history": updated_history,
        "chat_id": chat_id,
        "run_id": run_id,
    }
