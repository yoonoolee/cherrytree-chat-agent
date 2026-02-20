# Cofounder Advisor — AI Agent System

AI-powered advisory agent that helps users navigate complex cofounder situations, understand legal concepts, and fill out their cofounder agreement with contextual, scenario-based guidance.

## Implementation Status

### ✅ Completed (Local Development)
- [x] FastAPI server running on localhost:8000
- [x] Basic LangGraph agent orchestration
- [x] System prompt with optimized structure (identity → thinking → communication → operational)
- [x] Chat storage in Firestore (create, load, list, delete)
- [x] Test UI with ChatGPT-style centered layout
- [x] Conversation history persistence across sessions
- [x] Feedback mechanism (thumbs up/down)
- [x] AI safety guardrails (pronoun usage, data integrity, conversation memory)
- [x] Core endpoints: POST /chat, GET /health, GET /chat/{chat_id}, GET /chats/{user_id}, DELETE /chats/{chat_id}
- [x] LangSmith integration (currently disabled for testing)

### 🚧 In Progress / Next Steps
- [ ] **Knowledge Base (P0)** - 21 Cherrytree articles ingested into Pinecone. Need to add the rest. 
- [ ] **Fix RAG Tool Usage (P0)** - Agent not calling rag_search when it should
- [ ] **Verify Knowledge Base Content Quality (P0)** - Some articles may be summarized instead of full source
- [ ] **Additional Tools (P0)** - Implement suggest_form_value, calculate_equity
- [ ] **AI Safety Enhancements (P1)** - Add abuse/manipulation recognition, mental health boundaries
- [ ] **Evaluation Pipeline (P1)** - Implement retrieval precision, citation analysis, user feedback metrics
- [ ] **Production Auth (P0)** - Firebase Functions gateway with Clerk verification
- [ ] **React Component (P1)** - AdvisorChat.js sidebar for production UI
- [ ] **Rate Limiting (P0)** - Per-user and global limits
- [ ] **Cost Controls (P0)** - Spending limits, circuit breakers
- [ ] **Cloud Run Deployment (P1)** - Production deployment with secrets management
- [ ] **Monitoring (P1)** - Error tracking, observability, alerts
- [ ] **Advanced Agents** - Create Lawyer and VC Agents 

### ⚠️ Known Issues

**Evaluate RAG Tool Usage**
- Agent should be calling `rag_search` when answering cofounder questions more often.  
- Currently relying on general training data instead of Pinecone knowledge base more than it should. 
- Example: Asked "how to handle lazy cofounder" → agent answered without searching, even though relevant article exists
- **TODO:** Update system prompt to encourage/require RAG usage 
- **Alternatives:** Make rag_search mandatory for certain question types, adjust tool description

**Pinecone Content May Be Summaries (2026-02-11)**
- Some articles in knowledge_base.jsonl are condensed/summarized rather than full raw source text
- Currently testing out summaries vs raw source text, starting with summaries. If summaries don't work well then try raw source text. 
- **TODO:** Try using raw source text instead. 
- **Current state:** 21 articles (84 KB). Later ingest the rest of the documents after testing out summary vs raw source text. 

## Overview

- Embedded in the Survey page as a chat sidebar
- Handles complex situational questions ("I'm part-time, my cofounder put in $50K...")
- Retrieves relevant legal knowledge and scenario playbooks via RAG
- Reads and suggests form values based on the user's specific situation
- Multi-turn conversations with persistent memory across sessions
- Educational only — not legal advice

## Architecture

```
┌─────────────────────────────────────────────────┐
│                React Frontend                    │
│  ┌───────────┐  ┌──────────────────────────┐    │
│  │ Survey UI │  │ AdvisorChat (sidebar)     │    │
│  │           │  │  - Message history        │    │
│  │           │  │  - Suggested questions     │    │
│  │           │  │  - Feedback (thumbs)       │    │
│  │           │  │  - Legal disclaimer        │    │
│  └───────────┘  └──────────────────────────┘    │
└──────────────────────┬──────────────────────────┘
                       │
              Firebase Functions (Node.js)
              ┌────────┴────────┐
              │   API Gateway   │
              │  Auth + Routing │
              └────────┬────────┘
                       │
         Cloud Run Service (Python)
    ┌──────────────────┴──────────────────────┐
    │          LangGraph Orchestrator          │
    │                                          │
    │  ┌────────────────────────────────────┐  │
    │  │             Agent                  │  │
    │  │  - System prompt with XML tags     │  │
    │  │  - Chain-of-thought reasoning      │  │
    │  │  - Multi-turn conversation state   │  │
    │  └──────────────┬─────────────────────┘  │
    │                 │                         │
    │  ┌──────────────┴─────────────────────┐  │
    │  │           Tool Layer               │  │
    │  │  - RAG retrieval (Pinecone)        │  │
    │  │  - Read form data (Firestore)      │  │
    │  │  - Suggest form values             │  │
    │  │  - Equity scenario calculator      │  │
    │  │  - State law lookup                │  │
    │  └────────────────────────────────────┘  │
    └──────────────────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         │             │              │
    Claude API    Pinecone        Firestore
    (Anthropic)   (RAG vectors)   (chat history + form data)
```

### Why This Architecture

**LangGraph on Cloud Run (Python)** — Agent frameworks (LangGraph, LangChain) are Python-first with the most mature ecosystem. Running as a separate Cloud Run service keeps it cleanly isolated from the existing Firebase Functions (Node.js). Firebase Functions remain the API gateway for auth and routing.

**Single agent node to start** — LangGraph uses a graph structure where agents are nodes and edges define control flow. We start with one agent node. When complexity demands it, we add more nodes (e.g., separate Legal Advisor, Form Assistant, Review Agent) without refactoring — just add a node and an edge.

**Pinecone for RAG** — Complex situational questions ("I'm part-time with a kid, cofounder invested $50K") require retrieved context to answer well. The LLM's general training data gives shallow advice; retrieved scenario playbooks, legal patterns, and frameworks give specific, grounded guidance. Pinecone is fully managed (no infra to maintain), has a free tier, and fits our managed-services-everywhere pattern (Firebase, Clerk, Stripe).

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| LLM | Claude API (Anthropic Sonnet) | Best reasoning for complex scenarios |
| Agent Framework | LangGraph + LangChain (Python) | Graph-based orchestration, mature ecosystem |
| Vector DB | Pinecone (serverless) | Managed, free tier, no ops |
| Agent Runtime | Google Cloud Run | Scales to zero, GCP-native, containerized |
| API Gateway | Firebase Cloud Functions (Node.js) | Existing auth + routing layer |
| Chat Storage | Firestore | Real-time sync, existing infrastructure |
| Embeddings | OpenAI text-embedding-3-small | Cost-effective, high quality |
| Observability | LangSmith | Trace agent reasoning, monitor quality |
| Frontend | React component | Existing stack |

### Content Types to Index

| Content Type | Examples | Priority |
|---|---|---|
| **Scenario playbooks** | Part-time cofounders, family members as cofounders, unequal capital contributions, technical vs non-technical splits, solo founder adding a cofounder later | P0 |
| **Equity frameworks** | Slicing Pie methodology, fixed split models, milestone-based vesting, capital contribution credits, sweat equity valuation | P0 |
| **Legal patterns by state** | Delaware LLC defaults, California community property, NY partnership law, state-specific non-compete enforceability | P1 |
| **Common failure modes** | What goes wrong without buyout clauses, vesting disasters, IP assignment gaps, decision deadlock scenarios | P1 |
| **Templates & precedents** | YC cofounder agreement template, Stripe Atlas docs, Orrick open-source templates, NVCA standards | P1 |
| **Industry benchmarks** | Typical equity splits by role, standard vesting schedules, common cliff periods, market-rate salary deferrals | P2 |
| **FAQ & definitions** | What is vesting, what is a cliff, what is IP assignment, what is a shotgun clause | P2 |

### RAG Pipeline

```
User question
    → Embed with text-embedding-3-small
    → Query Pinecone (top 5 relevant chunks)
    → Inject retrieved context into <knowledge_context> tag
    → Claude generates response grounded in retrieved content
```

### Knowledge Base Maintenance

- Start with 50-100 curated documents (enough to cover common scenarios)
- Use eval pipeline + user feedback to identify gaps
- Add content iteratively based on real usage patterns
- Re-embed when documents are updated

## Agent Tools

The agent doesn't just chat — it takes actions through tools that LangGraph manages.

| Tool | What It Does | Example |
|---|---|---|
| `rag_search` | Search Pinecone for relevant legal knowledge and scenarios | "Find patterns for part-time cofounder equity splits" |
| `read_form_data` | Read the user's current survey responses from Firestore | "What has the user filled out for equity allocation?" |
| `suggest_form_value` | Propose a value for a form field (user must approve) | "Based on your situation, I'd suggest a 4-year vesting schedule" |
| `calculate_equity` | Run equity split scenarios using existing calculator logic | "Model a 60/40 split with the capital contribution factored in" |
| `check_completion` | Check survey progress and identify incomplete sections | "You're 60% done — sections 5, 7, and 9 still need attention" |
| `lookup_state_law` | Retrieve state-specific legal information | "Delaware LLCs default to equal profit sharing unless the operating agreement says otherwise" |

Tools are defined in LangGraph and the agent decides which to call based on the conversation. Users always approve before any form data is written.

## System Prompt Structure

```xml
<role>
  You are the Cherrytree Cofounder Advisor — an AI assistant that helps
  startup cofounders think through complex partnership decisions and fill
  out their cofounder agreement. You combine legal knowledge with practical
  startup experience to give specific, actionable guidance.
</role>

<agreement_context>
  Dynamic: injected from current form data per request
  Includes company info, equity split, vesting, roles, etc.
</agreement_context>

<current_context>
  Dynamic: current section, completion %, recent edits
</current_context>

<knowledge_context>
  Dynamic: RAG-retrieved documents relevant to the user's question
</knowledge_context>

<instructions>
  - Ask clarifying follow-up questions before giving advice on complex situations
  - Ground answers in retrieved knowledge — cite specific frameworks or patterns
  - Connect advice to the user's specific form data when relevant
  - Structure responses: direct answer → reasoning → what to consider → suggested next step
  - When suggesting form values, explain the reasoning and ask for approval
  - Remember prior conversation context — don't ask questions already answered
  - If you're unsure, say so — don't fabricate statistics or legal claims
</instructions>

<capabilities>
  - Explain legal concepts in plain language
  - Analyze specific cofounder situations with nuance
  - Suggest equity splits, vesting schedules, and clause language
  - Identify potential conflicts or gaps in the agreement
  - Compare common approaches (e.g., Slicing Pie vs fixed split)
  - Help think through edge cases (what if someone leaves, goes part-time, etc.)
</capabilities>

<limitations>
  - This is educational guidance, NOT legal advice
  - Cannot predict legal outcomes or guarantee enforceability
  - Cannot provide tax advice
  - Cannot replace consultation with a qualified attorney
  - Does not know the user's full personal/financial situation beyond what's shared
</limitations>

<style>
  - Conversational but substantive — not overly formal, not flippant
  - Use concrete examples and numbers when possible
  - Keep responses focused — answer the question, don't lecture
  - Use bullet points and short paragraphs for readability
  - When multiple approaches exist, present them as options with tradeoffs
</style>

<examples>
  3-5 few-shot examples covering:
  1. Simple definition question
  2. Complex situational question requiring follow-ups
  3. Form value suggestion with reasoning
</examples>
```

## Conversational Memory

Complex cofounder situations unfold over multiple turns. The agent needs to build up context and remember what was discussed.

### Short-term (within session)
- Full conversation history passed with each request
- LangGraph manages conversation state in the graph

### Long-term (across sessions)
- Chat history persisted in Firestore
- Pinecone stores embeddings of past conversations for semantic recall
- Agent can reference prior sessions: "Last time we discussed your equity split..."

### Firestore Structure

```
projects/
  {projectId}/
    chats/
      {chatId}/
        createdAt: timestamp
        updatedAt: timestamp
        messages: [
          { role: "user", content: "...", timestamp: ... },
          { role: "assistant", content: "...", timestamp: ... }
        ]
        metadata:
          section: "equity"
          messageCount: 12
          lastTopic: "part-time cofounder equity"
```

### Firestore Rules

Add to `firestore.rules`:
```
match /projects/{projectId}/chats/{chatId} {
  allow read, write: if isProjectMember(projectId);
}
```

## Safety & Governance

Critical for a product that gives guidance affecting real business relationships and legal agreements.

### Guardrails
- **Legal disclaimer** on every response: "This is educational guidance, not legal advice"
- **Confidence scoring** — agent rates its own confidence; low-confidence triggers "consult an attorney for this specific situation"
- **Scope boundaries** — refuses to advise on tax law, criminal matters, employment disputes outside cofounder context
- **Anti-hallucination** — explicit instruction to say "I don't know" rather than fabricate; ground answers in RAG-retrieved content
- **PII protection** — don't echo back sensitive personal information unnecessarily

### Audit & Observability
- **LangSmith tracing** — full reasoning trace for every agent interaction (which tools called, what was retrieved, how the response was constructed)
- **Cost tracking** — monitor token usage per conversation, per project
- **Error logging** — failed tool calls, retrieval misses, timeout handling
- **Usage analytics** — common question topics, sections with most questions, conversation length distribution

### Human-in-the-Loop
- **Thumbs up/down** on every response — stored in Firestore for eval
- **Flag for review** button — user can flag an answer that seems wrong
- **Feedback feeds eval pipeline** — flagged answers become test cases

## Evaluation Pipeline

Automated quality testing to ensure the agent gives good advice consistently. Uses deterministic metrics and real user feedback rather than LLM-as-judge approaches.

### Evaluation Metrics

| Metric | What It Measures | How It Works | Status |
|---|---|---|---|
| **Success@3** | RAG quality - does retrieval find at least one good article? | Query Pinecone with test questions. Binary: found relevant article in top 3? Target: 90%+ | ✅ Implemented |
| **Citation Rate** | Response grounding - does the agent reference source material? | Automated check: % of responses containing phrases/concepts from retrieved docs. Target: 90%+ | ⏸️ On hold - needs RAG tool to be called by agent first |
| **User Approval Rate** | Real-world quality - do users like the responses? | Track thumbs up/down ratio from production Firestore feedback. Target: 80%+ approval | ✅ Ready (needs production data) |
| **Response Format Checks** | Safety & structure - does response follow guidelines? | Rules-based: contains disclaimer, reasonable length, asks follow-ups when needed | ⏸️ On hold - needs RAG tool to be called by agent first |

**Current Results (2026-02-11):**
- Success@3: **90%** (9/10 test queries find relevant article)
- Retrieval scores: 0.82-0.88 (strong semantic similarity)

### Why Success@K Instead of Precision@K

**Success@K** (binary: did we find at least one good article?) is better for RAG than Precision@K because:
- Simpler: only need to define one relevant article per query
- Practical: RAG just needs ONE good source for the agent
- Industry standard: used by Pinecone, OpenAI for RAG evaluation
- Interpretable: 90% = 9 out of 10 queries worked

**Precision@K** would require labeling ALL relevant articles in the knowledge base for each query (time-consuming and subjective).

### Retrieval Evaluation Process

```python
# eval/test_retrieval.py
# Test cases with ground truth (which article should match)
TEST_CASES = [
    {"query": "How to handle lazy cofounder?", "relevant_ids": ["help-my-cofounder-is-lazy"]},
    {"query": "Chemistry vs credentials?", "relevant_ids": ["credentials-or-chemistry"]},
    # ... currently 10 test cases
]

# Query Pinecone, calculate Success@3
for test in TEST_CASES:
    results = index.search(test["query"], top_k=3)
    success = 1.0 if any(relevant_id in results for relevant_id in test["relevant_ids"]) else 0.0

success_rate = total_success / len(TEST_CASES)
```

**⚠️ TODO:** Expand test cases from 10 to 50+ to cover:
- All article topics comprehensively
- Edge cases and ambiguous queries
- Multiple phrasings of same question
- Questions requiring multiple relevant articles

### Citation Grounding Check

**⚠️ ON HOLD:** Citation testing requires the agent to actually call the RAG tool and use retrieved content. Currently the agent is not calling `rag_search` (see Known Issues). Once RAG tool usage is fixed, we can:
1. Capture real agent responses to test queries
2. Verify responses contain concepts from retrieved articles
3. Calculate citation rate to validate grounding

```python
# eval/test_citation.py (implemented, needs real responses to test)
def check_grounding(response, retrieved_docs):
    # Extract key concepts from source docs
    source_concepts = extract_key_phrases(retrieved_docs)

    # Count how many appear in response
    citations = sum(1 for concept in source_concepts
                   if concept.lower() in response.lower())

    return citations / len(source_concepts)  # 0-1 score
```

### User Feedback Analysis

```python
# eval/analyze_feedback.py
# Query Firestore for production feedback
thumbs_up = count_feedback(score=1)
thumbs_down = count_feedback(score=0)
approval_rate = thumbs_up / (thumbs_up + thumbs_down)

# Track over time, by topic, by section
```

### Test Categories (Current: 10 cases)

**Retrieval Tests (eval/test_retrieval.py):**
- Cofounder traits (3 queries): lazy, narcissist, paranoid
- Cofounder selection (3 queries): credentials vs chemistry, technical cofounder, what makes cofounder material
- Best practices (1 query): 15 rules
- Conflict resolution (1 query): how to destroy cofoundership
- Relationship dynamics (1 query): building great relationships
- Communication (1 query): avoiding tough conversations

**Agent Response Tests (planned):**
- Simple definitions - Accurate and concise answers citing source material
- Complex scenarios - Agent asks follow-ups, gives nuanced advice grounded in knowledge base
- Out-of-scope questions - Declines gracefully with appropriate boundaries
- Adversarial inputs - Maintains safety guardrails and legal disclaimers
- Form suggestions - Reasonable values with clear reasoning from retrieved context

## Frontend Component

### AdvisorChat.js

**Layout:** Slide-out sidebar on the right side of the survey page.

**Features:**
- Message history with scroll
- Input field with send button
- Loading state with typing indicator
- Suggested questions based on current section
- Thumbs up/down on each agent response
- Flag for review button
- Legal disclaimer footer
- Minimize/expand toggle
- Welcome message on first open

**State:**
- `messages` — display messages
- `conversationHistory` — API format for context
- `isLoading` — loading/typing state
- `input` — current input value
- `isOpen` — sidebar open/closed
- `feedback` — per-message thumbs up/down state

## File Structure

```
/cloud-run-agent/                  # Python Cloud Run service (NEW)
  Dockerfile
  requirements.txt
  main.py                          # FastAPI server
  /agent/
    graph.py                       # LangGraph orchestrator
    nodes.py                       # Agent node(s)
    tools.py                       # Tool definitions (RAG, form read/write, etc.)
    state.py                       # Conversation state schema
  /prompts/
    advisor_prompt.py              # System prompt builder
  /knowledge/
    ingest.py                      # Script to embed and upload docs to Pinecone
    /documents/                    # Raw knowledge base documents
  /eval/
    test_suite.py                  # Automated evaluation tests
    judge_prompt.py                # LLM-as-judge prompt

/functions/                        # Existing Firebase Functions
  index.js                         # Add chatWithAdvisor gateway function

/src/
  /components/
    AdvisorChat.js                 # Chat UI component (NEW)
```

## Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| Claude API (Sonnet) | ~$0.01-0.03 per message | Higher for complex multi-tool turns |
| Pinecone | Free tier (100K vectors) | More than enough for knowledge base |
| Cloud Run | ~$0/month at low traffic | Scales to zero when idle |
| OpenAI Embeddings | ~$0.02 per 1M tokens | One-time for indexing, tiny per-query cost |
| LangSmith | Free tier (5K traces/month) | Sufficient for early usage |
| Firestore | ~$0.02 per 100K reads | Negligible |

**Total estimated cost:** ~$0.02-0.05 per conversation (5-10 messages), scaling linearly with usage. No fixed infrastructure costs due to serverless architecture.

## Setup Steps

### 1. Accounts & API Keys
- Anthropic account + API key (console.anthropic.com)
- Pinecone account + API key (pinecone.io, free tier)
- OpenAI account + API key (for embeddings)
- LangSmith account (smith.langchain.com, free tier)

### 2. Cloud Run Agent Service
```bash
# Create the Python service
mkdir cloud-run-agent && cd cloud-run-agent
python -m venv venv && source venv/bin/activate
pip install langchain langgraph langchain-anthropic langchain-pinecone \
    pinecone-client fastapi uvicorn langsmith openai google-cloud-firestore

# Build and deploy
gcloud run deploy cofounder-advisor \
    --source . \
    --region us-west2 \
    --allow-unauthenticated=false \
    --set-secrets=ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,\
                  PINECONE_API_KEY=PINECONE_API_KEY:latest,\
                  OPENAI_API_KEY=OPENAI_API_KEY:latest
```

### 3. Knowledge Base
```bash
# Curate documents in /cloud-run-agent/knowledge/documents/
# Run ingestion script to embed and upload to Pinecone
python cloud-run-agent/knowledge/ingest.py
```

### 4. Firebase Integration
- Add `chatWithAdvisor` gateway function to `/functions/index.js`
- Set Cloud Run service URL as Firebase secret
- Update `firestore.rules` for chats subcollection

### 5. Frontend
- Create `AdvisorChat.js` component
- Integrate into `SurveyPage.js`

### 6. Evaluation
- Build initial test suite (50+ scenarios)
- Run eval pipeline before each prompt/knowledge change
- Set up LangSmith tracing for production monitoring

## Scaling Path

The architecture supports incremental expansion without refactoring:

| When | Do This |
|------|---------|
| **Day 1** | Single agent node, 50-100 knowledge docs, basic tools (RAG + read form data) |
| **Week 2-4** | Add form suggestion tool, expand knowledge base based on real questions |
| **Month 2** | Add evaluation pipeline, LangSmith observability, feedback collection |
| **Month 3+** | If single agent struggles with breadth, split into specialized agent nodes in LangGraph (Legal Advisor, Form Assistant, Review Agent). Same graph, just more nodes and routing edges. |
| **Ongoing** | Continuously add knowledge docs, tune prompts, expand test suite based on user feedback |

The infrastructure is built once. The ongoing work is content, tuning, and expansion.

## What to Customize

These are the files you'll edit as you tune the product. The infrastructure code (graph, server, ingestion) rarely needs to change.

### 1. Knowledge Base — `knowledge/documents/*.jsonl`

This is the biggest lever for answer quality. Add JSONL files with documents the agent retrieves during conversations.

**Format:**
```jsonl
{"id": "unique_id", "topic": "equity", "title": "Short Title", "content": "The actual content the agent will reference..."}
```

**What to add:**
- Scenario playbooks (part-time cofounders, family members, unequal capital, tech vs non-tech)
- Equity frameworks (Slicing Pie, fixed splits, milestone-based vesting)
- State-specific legal patterns (Delaware LLC defaults, California non-compete rules)
- Common failure modes (what goes wrong without buyout clauses, IP gaps)
- Templates and precedents (YC, Stripe Atlas, Orrick open-source)
- Industry benchmarks (typical splits by role, standard vesting, salary deferrals)

**After editing, re-run ingestion:**
```bash
cd cherrytree-chat-agent
source venv/bin/activate
python knowledge/ingest.py
```

Can be one file or split into multiple by topic (`equity.jsonl`, `vesting.jsonl`, `state_laws.jsonl`). Pinecone doesn't care — each line is an independent document.

### 2. System Prompt — `prompts/advisor_prompt.py`

Controls the agent's personality, behavior, and response style. Edit `build_system_prompt()` to change:

- **Role definition** — who the agent is and its expertise level
- **Instructions** — how it should handle complex questions, when to ask follow-ups
- **Capabilities** — what it tells users it can do
- **Limitations** — what it refuses to do (legal advice, tax, etc.)
- **Style** — tone, formatting, response length
- **Context injection** — what dynamic data gets injected per request (currently: section, completion %)

The prompt uses XML tags (`<role>`, `<instructions>`, etc.) — Claude is specifically trained to follow these well. Keep the structure, modify the content.

### 3. Tools — `agent/tools.py`

Add new tools by writing a function with the `@tool` decorator. The function name, parameters, and docstring are what Claude sees to decide when to call it.

**Currently active:**
- `rag_search` — searches Pinecone knowledge base
- `read_form_data` — reads project survey data from Firestore
- `check_completion` — checks survey progress

**To add later:**
- `suggest_form_value` — propose a value for a form field (user approves)
- `calculate_equity` — run equity split scenarios
- `lookup_state_law` — state-specific legal lookups

After adding a tool, add it to the `all_tools` list at the bottom of the file.

### 4. Agent Graph — `agent/graph.py`

Rarely needs editing. Change if you want to:
- Adjust Claude model (`claude-sonnet-4-5-20250929`)
- Change temperature (0.3 = focused, higher = more creative)
- Increase max_tokens for longer responses
- Add new agent nodes (for multi-agent split later)

### 5. Test UI — `static/index.html`

The local testing interface. Edit to:
- Change the section dropdown options
- Adjust styling
- Add new test controls

This is for development only — the production UI will be the React `AdvisorChat.js` component in the main Cherrytree app.

## When Moving to Production

Things that work fine for local testing but MUST be changed before real users touch this.

### 1. Authentication — user_id must come from auth, not the request body

**Current (local testing):** `user_id` is a text field in the test UI. Anyone can type any ID and access anyone's chat history.

**Production fix:** Add a Firebase Function gateway (`chatWithAdvisor`) in the `cherrytree-cofounder-agreement` repo that:
1. Receives the request from the React frontend with the user's Clerk session token
2. Verifies the token with Clerk (same pattern as existing Cloud Functions)
3. Extracts the real `user_id` from the verified token
4. Forwards the request to this Cloud Run service with the verified `user_id`
5. The user never controls or sees the `user_id` parameter

This is the same auth pattern already used by all existing Cherrytree Cloud Functions.

### 2. HTTPS and domain restrictions

**Current:** Server runs on `http://localhost:8000` with permissive CORS.

**Production fix:**
- Deploy to Cloud Run (HTTPS by default)
- Lock CORS origins to only `https://cherrytree.app` and `https://my.cherrytree.app`
- Require authentication on the Cloud Run service (only callable by Firebase Functions, not directly by browsers)

### 3. Rate limiting

**Current:** No rate limiting. Anyone can send unlimited requests.

**Production fix:** Add rate limiting either in the Firebase Function gateway or in this service:
- Per-user limit (e.g., 50 messages/hour)
- Per-project limit
- Global limit to cap API costs

### 4. API key management

**Current:** API keys in `.env` file on disk.

**Production fix:**
- All secrets stored in Google Cloud Secret Manager
- Cloud Run accesses them via `--set-secrets` flag (already shown in setup steps)
- No keys in code, environment files, or container images

### 5. Firestore security rules

**Current:** The Python service uses a service account with full Firestore access.

**Production fix:** Add Firestore security rules for the chat subcollection:
```
match /users/{userId}/chats/{projectId} {
  allow read, write: if request.auth != null && request.auth.uid == userId;
}
```
This ensures even if someone bypasses the API, Firestore itself rejects unauthorized access.

### 6. Error handling and monitoring

**Current:** Errors return raw stack traces via HTTP 500.

**Production fix:**
- Sanitize error responses (don't expose internal details)
- Set up LangSmith for agent observability
- Set up Cloud Logging / alerting for failures
- Add Sentry or similar for error tracking

### 7. Cost controls

**Current:** No spending limits. A runaway loop or abuse could rack up API costs.

**Production fix:**
- Set spending limits on the Anthropic account
- Monitor token usage per user/project via LangSmith
- Add a circuit breaker: if a single request exceeds N tool calls or N tokens, terminate it
- Alert on unusual usage patterns

---

## Immediate Next Steps (Prioritized)

### Phase 1: Core Functionality (Week 1-2)
**Goal:** Make the agent actually useful by giving it knowledge and tools

1. **Knowledge Base Ingestion (P0)**
   - Create 50-100 curated documents covering:
     - Scenario playbooks (part-time cofounders, family members, unequal capital)
     - Equity frameworks (Slicing Pie, fixed splits, milestone vesting)
     - Common failure modes and red flags
   - Format as JSONL in `knowledge/documents/`
   - Run `python knowledge/ingest.py` to embed and upload to Pinecone
   - **Blocker:** Without this, the agent is just generic ChatGPT

2. **Test the Agent (P0)**
   - Run through 10-15 realistic cofounder scenarios
   - Verify pronoun usage, response format, data integrity
   - Check that it uses RAG search appropriately
   - Document any issues or hallucinations

3. **AI Safety Enhancements (P1)**
   - Add to system prompt:
     - Abuse/manipulation pattern recognition
     - Mental health boundary guidance (suggest professional help when appropriate)
   - Test with adversarial inputs

### Phase 2: Production-Ready Tools (Week 3-4)
**Goal:** Enable the agent to actually help with form filling

4. **Implement Additional Tools**
   - `suggest_form_value` - Propose values for form fields with reasoning
   - `check_completion` - Identify incomplete survey sections
   - `calculate_equity` - Run equity split scenarios

5. **Evaluation Pipeline**
   - Build test suite with 50+ scenario questions
   - Set up LLM-as-judge for automated scoring
   - Run regression tests before prompt/knowledge changes

### Phase 3: Production Deployment (Week 5-6)
**Goal:** Ship to real users safely

6. **Authentication & Security**
   - Create Firebase Function gateway with Clerk verification
   - Lock down CORS to production domains only
   - Add Firestore security rules for chat subcollection

7. **Rate Limiting & Cost Controls**
   - Per-user limits (50 messages/hour)
   - Circuit breaker for runaway requests
   - Spending alerts on Anthropic account

8. **Cloud Run Deployment**
   - Deploy to Cloud Run with secrets management
   - Set up monitoring and error tracking
   - Configure auto-scaling

9. **React Frontend Component**
   - Build `AdvisorChat.js` sidebar component
   - Integrate into Survey page
   - Add suggested questions based on current section

### Phase 4: Iterate & Improve (Ongoing)
**Goal:** Continuously improve based on real usage

10. **Monitor & Tune**
    - Re-enable LangSmith for observability
    - Analyze user feedback (thumbs up/down)
    - Identify knowledge gaps from real questions
    - Expand knowledge base based on usage patterns

11. **Advanced Features** (Future)
    - Multi-agent split (Legal Advisor, Form Assistant, Review Agent)
    - State-specific law lookup tool
    - Equity calculator integration
    - Long-term memory across projects

---

## Planned Agent Expansions

### Lawyer Agent (Planned)

The core advisor is intentionally kept accessible and educational. The Lawyer Agent is a planned expansion focused on deeper legal analysis — things like interpreting specific clause language, flagging enforceability issues by state, and surfacing relevant legal precedents. The goal is to help users understand the legal weight of what they're agreeing to, while always making clear this is educational guidance and not a substitute for an actual attorney.

### VC Agent (Planned)

Many cofounder agreement decisions have downstream effects on fundraising that founders don't always think about upfront — equity splits, vesting structures, and control provisions all come up in investor due diligence. The VC Agent is a planned expansion to help cofounders understand how their agreement looks from an investor's perspective and what to think through before they lock anything in.

---

## Quick Wins for This Week

1. **Create initial knowledge base** (10-20 documents minimum)
   - Focus on most common scenarios: equity splits, vesting, part-time cofounders
   - Test that RAG retrieval works

2. **Add mental health/abuse safety guardrails** to system prompt
   - Pattern recognition for manipulation/harassment
   - Guidance to redirect to appropriate professional help

3. **Run manual testing** with realistic scenarios
   - Document what works, what doesn't
   - Build initial test cases for eval pipeline
