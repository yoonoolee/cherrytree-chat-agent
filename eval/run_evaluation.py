"""
Cherrytree Advisor Evaluation Runner

Pulls the dataset from LangSmith, runs the agent against each test case,
scores results with evaluators, and pushes scores back to LangSmith.

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python eval/run_evaluation.py [--experiment-name "my-run"]

View results at: https://smith.langchain.com/ → Datasets → cherrytree-advisor-evals
"""

import asyncio
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

from langsmith import evaluate, Client
from langchain_core.runnables import RunnableLambda

from agent.graph import graph, RAG_TOPICS
from prompts.advisor_prompt import build_system_prompt
from eval.evaluators import EVALUATORS

DATASET_NAME = "cherrytree-advisor-evals"


# ---------------------------------------------------------------------------
# Target function — runs the agent for a single eval input
# ---------------------------------------------------------------------------

async def _run_agent_async(inputs: dict) -> dict:
    """
    Run the agent against a single eval test case.
    Bypasses Firestore — uses survey_context and conversation directly from inputs.
    """
    conversation = inputs.get("conversation", [])
    survey_context = inputs.get("survey_context", {})
    current_section = inputs.get("current_section", "")

    # Build messages from conversation history
    messages = [{"role": m["role"], "content": m["content"]} for m in conversation]

    result = await graph.ainvoke({
        "messages": messages,
        "project_id": "eval",
        "current_section": current_section,
        "survey_context": survey_context,
        "response": "",
    })

    response = result.get("response", "")

    # Extract tool calls from the graph result for rag_called eval
    tool_calls = []
    for msg in result.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"name": tc.get("name", "")})

    return {
        "response": response,
        "tool_calls": tool_calls,
    }


def run_agent_for_eval(inputs: dict) -> dict:
    """Sync wrapper for the async agent runner."""
    return asyncio.run(_run_agent_async(inputs))


# ---------------------------------------------------------------------------
# Evaluator wrapper — routes each example to only its applicable evaluators
# ---------------------------------------------------------------------------

def make_evaluator(key: str):
    """Wrap a single evaluator function so it skips examples that don't need it."""
    fn = EVALUATORS[key]
    def wrapped(run, example):
        return fn(run, example)
    wrapped.__name__ = key
    return wrapped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(experiment_name: str = None):
    if not experiment_name:
        experiment_name = f"eval-{datetime.now().strftime('%Y%m%d-%H%M')}"

    print(f"\nRunning eval experiment: {experiment_name}")
    print(f"Dataset: {DATASET_NAME}")
    print(f"View at: https://smith.langchain.com/\n")

    # All evaluators — each one checks if it applies to the example internally
    evaluators = [make_evaluator(k) for k in EVALUATORS]

    results = evaluate(
        run_agent_for_eval,
        data=DATASET_NAME,
        evaluators=evaluators,
        experiment_prefix=experiment_name,
        max_concurrency=3,
    )

    # Print summary
    print(f"\n{'─' * 60}")
    print(f"Experiment complete: {experiment_name}")
    print(f"{'─' * 60}")

    scores = {}
    for result in results:
        for feedback in result.get("feedback", []):
            key = feedback.key
            score = feedback.score
            if score is not None:
                if key not in scores:
                    scores[key] = []
                scores[key].append(score)

    if scores:
        print(f"\n{'Evaluator':<30} {'Avg Score':<12} {'Count'}")
        print(f"{'─' * 55}")
        for key in sorted(scores):
            vals = scores[key]
            avg = sum(vals) / len(vals)
            print(f"{key:<30} {avg:<12.2f} {len(vals)}")
    else:
        print("No scores returned — check LangSmith for results.")

    print(f"\nFull results: https://smith.langchain.com/\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-name", type=str, default=None)
    args = parser.parse_args()
    main(experiment_name=args.experiment_name)
