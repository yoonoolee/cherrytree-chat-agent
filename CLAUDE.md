# cherrytree-chat-agent — Claude Context

Python/FastAPI AI advisor service. Runs on Google Cloud Run. Integrated into the Cherrytree web app as a chat sidebar.

## Stack

- **LLM:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Agent framework:** LangGraph (ReAct pattern — reason → tool call → reason)
- **Vector DB:** Pinecone (RAG, top-k=100, score threshold 0.80 — returns all docs then filters by relevance)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Chat storage:** Firestore (`projects/{projectId}/chats/{chatId}`)
- **Observability:** LangSmith
- **Rate limiting:** slowapi (20/min + 200/hour per IP on `/chat` — blocks burst and sustained abuse)
- **Runtime:** Google Cloud Run (us-west2), scales to zero

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI entry point. Routes: `/chat`, `/health`, `/chats`, `/feedback` |
| `agent/graph.py` | LangGraph graph definition, model config, ReAct loop |
| `agent/state.py` | `AgentState` schema (messages, project_id, section, completion %) |
| `agent/tools.py` | Tool definitions — `rag_search`, `read_form_data`, `check_completion` |
| `agent/chat_store.py` | Firestore read/write for chat history |
| `agent/services.py` | Pinecone + Firestore client initialization |
| `prompts/advisor_prompt.py` | System prompt builder (XML-structured, ~150 lines, injected with dynamic context) |
| `knowledge/documents/knowledge_base.jsonl` | 21 curated articles on cofounder scenarios |
| `knowledge/ingest.py` | Embeds docs and uploads to Pinecone |
| `eval/run_evaluation.py` | Master eval runner |
| `eval/test_retrieval.py` | Measures RAG Success@3 |
| `eval/test_citation.py` | Measures citation grounding |

## Local Dev

```bash
source venv/bin/activate
cp .env.example .env  # fill in keys first time
uvicorn main:app --reload
# → http://localhost:8000 (test UI) or POST /chat
```

## Agent Use Cases

The agent is a full cofounder advisor — covering both the legal/structural agreement AND the relationship dynamics between cofounders. It is not scoped to just the section the user is currently on. Users can:

- **Ask educational questions** — "what is a cliff?", "how does a shotgun clause work?", "what's the difference between single and double-trigger acceleration?"
- **Get advice on what to fill in** — based on their specific situation (roles, commitment level, relationship history), the agent can help them think through what answers make sense for them
- **Discuss their specific situation** — users describe their cofounder setup and get tailored input on what it means for their agreement
- **Get suggestions on what to discuss with their cofounder** — the agent can surface conversations worth having, either in general or based on gaps/tensions in the form data they've entered
- **Discover things to add beyond the survey** — the agent can flag additional clauses, considerations, or protections that aren't in the standard form but may matter for their situation
- **Ask about any part of the agreement at any time** — they're not limited to their current survey section; the agent advises across Formation, Equity, Vesting, Decision-Making, IP, Compensation, Performance, Non-Compete, and General Provisions

## Agent Tools

1. **`rag_search`** — semantic search over Pinecone knowledge base
2. **`read_form_data`** — fetch user's current survey answers from Firestore
3. **`check_completion`** — report which sections are complete/incomplete

Planned (not yet built): `suggest_form_value`, `calculate_equity`, `lookup_state_law`

## Known Issues

- **Small knowledge base:** Only 21 articles ingested. More pending after validating summaries vs. raw text format.
- **Citation grounding eval:** Pending more knowledge base content.

## Adding a Tool

1. Define it with `@tool` decorator in `agent/tools.py`
2. Add it to the tools list in `agent/graph.py`
3. Update `prompts/advisor_prompt.py` capabilities section if needed
4. Re-ingest knowledge if adding domain content: `python knowledge/ingest.py`

## System Prompt Design

- XML-structured (`<role>`, `<instructions>`, `<capabilities>`, `<limitations>`)
- Dynamically injected: current section, completion %, project context
- Key constraints: educational only (not legal advice), pronoun-neutral (they/them default), always recommend consulting a lawyer

## Knowledge Content to Index

Priority order for expanding the knowledge base beyond the current 21 articles:

| Content Type | Examples | Priority |
|---|---|---|
| Scenario playbooks | Part-time cofounders, family members, unequal capital, tech vs non-tech | P0 |
| Equity frameworks | Slicing Pie, fixed splits, milestone vesting, capital contribution credits | P0 |
| Common failure modes | No buyout clause, vesting disasters, IP assignment gaps, decision deadlock | P1 |
| Legal patterns by state | Delaware LLC defaults, CA non-compete rules, NY partnership law | P1 |
| Templates & precedents | YC agreement, Stripe Atlas, Orrick open-source templates | P1 |
| Industry benchmarks | Typical equity splits by role, standard vesting, salary deferrals | P2 |
| FAQ & definitions | What is vesting, cliff, IP assignment, shotgun clause | P2 |

Format for JSONL documents:
```jsonl
{"id": "unique-slug", "topic": "equity", "title": "Short Title", "content": "Full content here..."}
```

After adding docs: `python knowledge/ingest.py` to embed and upload to Pinecone.

Currently testing **summaries vs. raw source text** — 21 summary articles ingested. Switch to raw source if quality is insufficient.

## Production Readiness

See `TODO.md` for the full pre-launch checklist including Cloud Run deployment steps, the Firebase Function gateway (auth fix), and cost controls.

## Roadmap

**Phase 1 — Make the agent useful (current focus)**
- Expand knowledge base to 50-100 articles (P0)
- Implement `suggest_form_value` and `calculate_equity` tools (P0)
- Add abuse/mental health boundary guardrails to system prompt (P1)

**Phase 2 — Production-ready**
- Firebase Function gateway with Clerk auth
- Rate limiting + cost controls
- Cloud Run deployment with Secret Manager
- Build `AdvisorChat.js` React component and integrate into Survey page

**Phase 3 — Iterate**
- Re-enable LangSmith, analyze user feedback
- Expand eval test suite from 10 → 50+ cases
- Add state law lookup tool

**Future agents (planned)**
- **Lawyer Agent** — deeper legal analysis, clause interpretation, enforceability by state
- **VC Agent** — investor perspective on agreement terms, fundraising implications

## Platform Overview

Cherrytree is a SaaS platform for startup cofounders to build strong cofounder partnerships — covering both the legal/structural agreement and the relationship dynamics between cofounders. Two subprojects work together:

| Directory | Role | Stack |
|-----------|------|-------|
| `cherrytree-cofounder-agreement/` | Main web app (frontend + backend) | React 19, Firebase, Clerk, Stripe |
| `cherrytree-chat-agent/` | AI advisor chatbot service | Python, FastAPI, LangGraph, Claude, Pinecone |

The web app embeds the chat agent as a sidebar. The agent reads the user's in-progress agreement from Firestore and advises on both structural topics (equity, vesting, IP, decision-making) and relationship topics (cofounder dynamics, conflict resolution, communication, partner selection).

## High-Level Architecture

```
User → React app (Firebase Hosting)
         ├── Firestore (form data, chat history, orgs)
         ├── Cloud Functions (Node.js, us-west2) — business logic, webhooks
         └── Chat sidebar → Cloud Run (Python FastAPI) — LangGraph agent
                               ├── Claude Sonnet 4.5 (LLM)
                               ├── Pinecone (RAG knowledge base)
                               └── Firestore (chat history)
```

## Environments

| Env | Firebase Project | Frontend URL |
|-----|-----------------|-------------|
| Dev | `cherrytree-cofounder-agree-dev` | cherrytree-cofounder-agree-dev.web.app |
| Prod | `cherrytree-cofounder-agreement` | cherrytree.app / my.cherrytree.app |

Switch with: `firebase use dev` or `firebase use prod`

## Secrets

Never commit API keys. All keys are in:
- `.env.development` / `.env.production` (frontend, git-ignored)
- Firebase Secret Manager (Cloud Functions)
- Cloud Run Secret Manager (Python agent: Anthropic, Pinecone, LangSmith keys)

## Code Standards (Apply to Every Task)

**No hardcoded local paths:** Never hardcode user-specific paths in any committed file — commands, configs, or docs. Always use relative paths or project-root-relative paths so everything works for any teammate on any machine.

**No duplicate work:** Before suggesting or creating anything (commands, files, functions, configs), check if it already exists. If something exists but the user can't find it, help them locate or access it — don't recreate it.

**Best practices:** Always flag if something deviates from best practices — naming conventions, code structure, anti-patterns, performance issues, or anything that would be considered poor engineering. Don't just complete the task silently; call it out and suggest the better approach.

**Security:** On every task, do a quick security check on any code touched — exposed secrets, injection vulnerabilities (NoSQL/SQL/XSS), unauthenticated endpoints, insecure Firestore rules, CORS misconfiguration, hardcoded credentials. Flag anything suspicious even if outside the immediate scope of the change.

## Team Collaboration

Two people actively pushing to this repo. When working with Claude:

- **Always confirm the Firebase environment** before deploying — `firebase use` to check current target. Default to dev unless explicitly deploying to prod.
- **Don't assume solo context** — changes may affect the other developer. Flag anything that would break shared state (Firestore schema changes, Cloud Function renames, config changes).
- **Coordinate on secrets** — both devs need matching `.env.development` / `.env.production` files locally. These are gitignored; share keys out-of-band.
- **`.claude/settings.json` is committed** — changes to Claude permissions/commands apply to both teammates. Don't add personal preferences here; use `settings.local.json` (gitignored) for those.
- **`.claude/commands/` is committed** — shared slash commands available to both teammates.

