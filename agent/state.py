"""
Conversation state schema for LangGraph.

This defines the "shape" of data that flows through the graph.
Every node in the graph receives this state and can read/update it.
Think of it as a shared data object that gets passed from node to node.
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State that flows through the LangGraph graph."""

    # The conversation messages (user messages, assistant responses, tool results).
    # Annotated with add_messages tells LangGraph to APPEND new messages
    # instead of replacing the entire list — this is how conversation history builds up.
    messages: Annotated[list, add_messages]

    # Project context — passed in from the frontend so the agent
    # knows which project it's advising on and where the user is in the survey.
    project_id: str
    current_section: str
    survey_context: dict

    # The final text response from the agent — extracted at the end
    # and sent back to the frontend.
    response: str
