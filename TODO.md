# TODO — cherrytree-chat-agent

---

## Before Production Launch (required)

### 1. Deploy to Cloud Run
The agent currently only runs locally. Steps to deploy to dev:

1. Install `gcloud` CLI if not already: https://cloud.google.com/sdk/docs/install
2. Authenticate: `gcloud auth login`
3. Set project: `gcloud config set project cherrytree-cofounder-agree-dev`
4. Add secrets to Secret Manager (do once per project):
   ```bash
   gcloud secrets create ANTHROPIC_API_KEY --data-file=-   # paste key, Ctrl+D
   gcloud secrets create PINECONE_API_KEY --data-file=-
   gcloud secrets create OPENAI_API_KEY --data-file=-
   gcloud secrets create LANGSMITH_API_KEY --data-file=-
   ```
5. Build and deploy:
   ```bash
   gcloud builds submit --tag gcr.io/cherrytree-cofounder-agree-dev/cherrytree-chat-agent
   gcloud run deploy cherrytree-chat-agent \
     --image gcr.io/cherrytree-cofounder-agree-dev/cherrytree-chat-agent \
     --region us-west2 \
     --set-env-vars ENVIRONMENT=development \
     --set-secrets=ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,PINECONE_API_KEY=PINECONE_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,LANGSMITH_API_KEY=LANGSMITH_API_KEY:latest \
     --allow-unauthenticated
   ```
6. Note the Cloud Run URL from the output — needed for step 2 below.

---

### 2. Wire Up the Firebase Function Gateway (auth fix)
Currently `user_id` comes from the request body — any user can impersonate another.
The gateway verifies the Clerk JWT server-side and injects the real `user_id`.

Once Cloud Run is deployed:
1. Set the secret in Firebase (both dev and prod):
   ```bash
   cd ../cherrytree-cofounder-agreement
   firebase use dev
   firebase functions:secrets:set CHAT_AGENT_URL   # paste Cloud Run URL
   firebase use prod
   firebase functions:secrets:set CHAT_AGENT_URL   # paste prod Cloud Run URL
   ```
2. Add `chatWithAdvisor` Cloud Function to `functions/index.js` — the code was already written and reviewed. Pattern is identical to `submitSurvey`: verify Clerk JWT via `verifyClerkToken(sessionToken)`, extract `userId`, forward request to Cloud Run with verified `userId`. Also add `const CHAT_AGENT_URL = defineSecret('CHAT_AGENT_URL')` to the secrets block at the top.
3. Update the React frontend (`AdvisorChat.js`) to call the `chatWithAdvisor` Cloud Function via `httpsCallable` instead of calling Cloud Run directly.
4. Deploy functions: push to `dev` branch or run `/deploy-functions-dev`.

---

### 3. Rate Limiting
Already implemented (60 msg/hour per IP via `slowapi`). Verify it's working after first Cloud Run deploy by checking response headers for `X-RateLimit-*`.

Consider tightening limits once you have real usage data.

---

### 4. CORS
Already environment-aware — prod only allows `cherrytree.app` and `my.cherrytree.app`. Verify `ENVIRONMENT=production` is set on the prod Cloud Run service.

---

### 5. Cost Controls
Set a spend limit on the Anthropic account to avoid surprise bills from abuse.

---

## Agent Quality (current focus)

- Fix RAG tool underuse — agent doesn't call `rag_search` frequently enough
- Expand knowledge base from 21 → 50-100 articles
- Build `AdvisorChat.js` React component and integrate into Survey page
- Implement `suggest_form_value` and `calculate_equity` tools

---

## Completed

- [x] FastAPI server with `/chat`, `/health`, `/chats`, `/feedback` endpoints
- [x] LangGraph ReAct agent with 3 tools (rag_search, read_form_data, check_completion)
- [x] Pinecone knowledge base (21 articles ingested)
- [x] LangSmith observability
- [x] Firestore chat history storage
- [x] Rate limiting (slowapi, 60/hr per IP)
- [x] CORS locked to prod domains (env-aware)
- [x] Error responses sanitized (no stack traces exposed)
- [x] Firestore security rules added for chats subcollection
- [x] .dockerignore (secrets excluded from Docker image)
