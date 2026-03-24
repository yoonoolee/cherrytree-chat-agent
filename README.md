# Cherrytree Chat Agent

AI-powered advisor that helps startup cofounders navigate cofounder agreements. Runs as a Python/FastAPI service on Google Cloud Run, integrated into the Cherrytree web app as a chat sidebar.

## What It Does

- Answers questions about equity splits, vesting, IP, decision-making, and dispute resolution
- Retrieves relevant knowledge from a curated article database (Pinecone RAG)
- Reads the user's in-progress cofounder agreement from Firestore for context
- Suggests form values and explains the reasoning
- Maintains conversation history across sessions

## Stack

- **Agent framework:** LangGraph + LangChain (Python)
- **LLM:** Claude (Anthropic)
- **Vector DB:** Pinecone (RAG)
- **Chat storage:** Firestore
- **Runtime:** Google Cloud Run
- **Observability:** LangSmith

## Project Structure

```
agent/          LangGraph orchestrator, tools, and state
prompts/        System prompt builder
knowledge/      Knowledge base documents and Pinecone ingestion scripts
eval/           Retrieval and citation evaluation pipeline
static/         Local test UI
main.py         FastAPI server entry point
```

## Local Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
uvicorn main:app --reload
```

Open `http://localhost:8000` for the test UI or send requests to `POST /chat`.

## Key Files to Customize

| File | What to change |
|------|---------------|
| `knowledge/documents/knowledge_base.jsonl` | Add/edit knowledge base articles |
| `prompts/advisor_prompt.py` | Tune agent personality and instructions |
| `agent/tools.py` | Add new tools the agent can call |
| `agent/graph.py` | Adjust model, temperature, token limits |

See `CLAUDE.md` for full architecture details and evaluation pipeline.
