# TODO — cherrytree-chat-agent

---

## Agent Quality (current focus)

- Expand knowledge base from 21 → 50-100 articles
- Build `AdvisorChat.js` React component and integrate into Survey page
- Implement `suggest_form_value` and `calculate_equity` tools

---

## Before Production Launch

### 1. Wire Up the Firebase Function Gateway (auth fix)
Currently `user_id` comes from the request body — any user can impersonate another.
The gateway verifies the Clerk JWT server-side and injects the real `user_id`.

1. Set the secret in Firebase (both dev and prod):
   ```bash
   cd ../cherrytree-cofounder-agreement
   firebase use dev
   firebase functions:secrets:set CHAT_AGENT_URL   # paste Cloud Run URL
   firebase use prod
   firebase functions:secrets:set CHAT_AGENT_URL   # paste prod Cloud Run URL
   ```
2. Add `chatWithAdvisor` Cloud Function to `functions/index.js` — verify Clerk JWT via `verifyClerkToken(sessionToken)`, extract `userId`, forward request to Cloud Run with verified `userId`.
3. Update React frontend (`AdvisorChat.js`) to call `chatWithAdvisor` via `httpsCallable` instead of calling Cloud Run directly.
4. Deploy functions: `/deploy-functions-dev`.

### 2. Rate Limiting
Already implemented (20/min + 200/hour per IP via `slowapi`). Verify it's working after Cloud Run deploy by checking response headers for `X-RateLimit-*`.

### 3. CORS
Already environment-aware — prod only allows `cherrytree.app` and `my.cherrytree.app`. Verify `ENVIRONMENT=production` is set on the prod Cloud Run service.

### 4. Cost Controls
Set a spend limit on the Anthropic account to avoid surprise bills from abuse.

---

## Future Agents

### VC Agent
An agent that looks at a cofounder agreement through an investor lens. Given the agreement terms, it can flag things that VCs typically push back on (single-trigger acceleration, unusual equity splits, missing IP assignment), explain what investors expect to see at different stages, and help founders anticipate due diligence questions before they're in a room with a VC. Could also simulate how a term sheet might interact with their existing cofounder agreement.

### Proactive Advisor Agent
A background agent that continuously watches the user's survey answers and surfaces comments and flags without the user having to ask. At the start of their session, users provide context about their specific situation (relationship history, company stage, roles, goals) — the agent uses that to make its feedback relevant rather than generic. As fields get filled in, it proactively identifies tensions, missing pieces, or things worth discussing with their cofounder. Different from the chatbot: the user doesn't trigger it, it just watches and annotates.

### Comments Agent
Users can leave comments anywhere in their agreement (on a clause, a field, a section). A Comments Agent monitors new comments and can respond — explaining what a clause means, flagging a potential issue, or prompting a conversation the cofounders should have. Could also notify the other cofounder when a comment is left, turning the agreement into a shared workspace rather than a solo form.

---

## Completed

- [x] FastAPI server with `/chat`, `/chat/stream`, `/health`, `/chats`, `/feedback` endpoints
- [x] LangGraph ReAct agent with 3 tools (rag_search, read_form_data, check_completion)
- [x] Streaming endpoint with SSE
- [x] Live survey context fetched from Firestore on every message
- [x] Pinecone knowledge base (21 articles ingested)
- [x] LangSmith observability
- [x] Firestore chat history storage
- [x] Rate limiting (slowapi, 20/min + 200/hour per IP)
- [x] CORS locked to prod domains (env-aware)
- [x] Error responses sanitized (no stack traces exposed)
- [x] Firestore security rules added for chats subcollection
- [x] .dockerignore (secrets excluded from Docker image)
