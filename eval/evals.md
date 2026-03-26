# Evaluation Plan

Evals run via `eval/run_evaluation.py` against a LangSmith dataset. Each test case is a conversation (list of messages) with a ground truth label and expected behavior description. The last message in the conversation is the one being evaluated.

## Current Evals

### 1. Query Type Classification
- Predicted type list (emitted as `<query_type>` tag in response) matches ground truth list
- Types can be a single value, multiple, or none
- **Method:** Programmatic — parse tag, compare against ground truth list

### 2. Response Mode
- What is the response doing: answering, analyzing, asking followups, giving next steps, or a mix
- Compare against expected mode(s) defined in dataset
- **Method:** LLM-as-judge

### 3. Filler Phrases
- Response contains none of: "I hear you", "that's a great question", "I understand", "absolutely", "certainly", "of course"
- **Method:** Programmatic string match

### 4. EDU / BENCH — RAG usage
- Agent called `rag_search` before answering
- **Method:** Programmatic via LangSmith trace tool call inspection

### 5. EDU / BENCH — No fabricated stats
- Response does not contain made-up percentages, statistics, or specific data points
- **Method:** LLM-as-judge

### 6. EDU / BENCH — Source citation
- Response cites a named source when making a claim (e.g. "YC generally recommends...", "According to NVCA templates...")
- **Method:** LLM-as-judge

### 7. SIT_A / SIT_E — Follow-up question quality
- When the agent asks for more context, the follow-up question is relevant and focused
- Compare against expected follow-up intent defined in dataset
- **Method:** LLM-as-judge

### 8. SIT_E — Response stance
- Expected stance defined in dataset: reassuring / asking followups / flagging bad situation
- Did the response match the expected stance?
- **Method:** LLM-as-judge

### 9. ACT — Next step quality
- Is the next step specific, actionable, and appropriate for the situation?
- Compare against expected next step intent defined in dataset
- **Method:** LLM-as-judge

### 10. FORM / REVIEW — Agreement field references
- Which specific agreement fields were referenced (list)
- Quality of analysis given those fields
- Compare against expected fields and analysis intent defined in dataset
- **Method:** LLM-as-judge

### 11. GUARD — Decline and redirect
- Agent declined the off-topic or out-of-scope request
- Agent redirected to cofounder topics
- **Method:** LLM-as-judge

---

## TODO

### Tone and language quality
- Response does not sound AI-generated (overly formal, structured, or robotic)
- Tone matches the situation (warm for SIT_E, direct for ACT, educational for EDU)
- **Method:** LLM-as-judge
- **Status:** Deferred — implement after core evals are stable

### RAG retrieval quality
- For a given query, is the relevant document in the top k results? (Success@k)
- Does the response use what was retrieved, or ignore it and answer from model knowledge? (grounding)
- **Method:** Success@k programmatic, grounding via LLM-as-judge
- **Status:** Deferred — implement after knowledge base expands to 50+ docs
