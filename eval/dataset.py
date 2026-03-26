"""
LangSmith Dataset Builder

Reads test cases from cases.json and uploads them to LangSmith as a named dataset.
To add or edit cases, edit cases.json and re-run this script.

Usage:
    cd cherrytree-chat-agent
    source venv/bin/activate
    python eval/dataset.py
"""

import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client

load_dotenv(override=True)

DATASET_NAME = "cherrytree-advisor-evals"
CASES_FILE = Path(__file__).parent / "cases.json"


def load_cases():
    """Load test cases from cases.json, stripping JS-style // comments."""
    raw = CASES_FILE.read_text()
    stripped = re.sub(r"//.*", "", raw)
    return json.loads(stripped)


def create_or_update_dataset():
    client = Client()
    cases = load_cases()

    # Get or create the dataset
    datasets = list(client.list_datasets(dataset_name=DATASET_NAME))
    if datasets:
        dataset = datasets[0]
        print(f"Found existing dataset: {DATASET_NAME} ({dataset.id})")
        existing = list(client.list_examples(dataset_id=dataset.id))
        if existing:
            client.delete_examples([e.id for e in existing])
            print(f"Cleared {len(existing)} existing examples")
    else:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Cherrytree cofounder advisor eval cases — one or more per query type"
        )
        print(f"Created dataset: {DATASET_NAME} ({dataset.id})")

    client.create_examples(
        dataset_id=dataset.id,
        inputs=[c["inputs"] for c in cases],
        outputs=[c["outputs"] for c in cases],
        metadata=[c["metadata"] for c in cases],
    )

    print(f"Uploaded {len(cases)} test cases")
    print(f"View at: https://smith.langchain.com/ → Datasets → {DATASET_NAME}")


if __name__ == "__main__":
    create_or_update_dataset()
