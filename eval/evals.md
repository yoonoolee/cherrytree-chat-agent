# Evaluation Plan

Evals run via `eval/run_evaluation.py` against a LangSmith dataset (`cherrytree-advisor-evals`).
Each test case is a conversation with `eval_checks` — a typed dict of expected behaviors.
The last message in the conversation is the one being evaluated.

## Evaluator Types

| Method | Description |
|--------|-------------|
| Programmatic | Deterministic — parses output or inspects LangSmith trace |
| LLM-as-judge | Single Haiku call per test case, evaluates all applicable checks at once |

## eval_checks Value Types

| Type | Meaning | Scoring |
|------|---------|---------|
| `false` | Strictly absent — wrong if present | 1 if absent, 0 if present |
| `true` / `"description"` / `["list"]` | Required / expected | 0=poor, 0.5=adequate, 1=excellent |
| `"It is acceptable..."` string | Optional — absent is fine, present is evaluated | NOT_PRESENT=1, PRESENT_CORRECT=0.75, PRESENT_WRONG=0.25 |

The `"It is acceptable"` prefix is the programmatic signal for optional checks. The full description also tells the judge what "correct" looks like if the behavior does appear.

## Evaluators

All 12 evaluators apply to all 8 query types (EDU, BENCH, FORM, SIT_A, SIT_E, ACT, REVIEW, GUARD).

### 1. query_type
- Did the model classify the query correctly?
- Parsed from `<query_type>...</query_type>` tag emitted in response (stripped from UI)
- Exact match → 1, partial overlap → 0.5, wrong → 0
- **Method:** Programmatic

### 2. is_rag_called
- Did the agent call `rag_search` — or correctly not call it?
- **Method:** Programmatic (LangSmith trace inspection)

### 3. response_mode
- Did the response use the right mode(s)? (`answering`, `analyzing`, `asking_followups`, `giving_next_steps`)
- Multiple modes allowed
- **Method:** LLM-as-judge

### 4. no_fabricated_stats
- Did the response avoid made-up percentages, statistics, or specific data points?
- Qualitative observations and explicitly named sources are acceptable
- **Method:** LLM-as-judge

### 5. is_source_cited
- Did the response cite a named source when expected — or correctly avoid citing when not?
- Named source = explicitly mentions YC, NVCA, specific founders, named studies, etc.
- **Method:** LLM-as-judge

### 6. answering_quality
- Did the response answer correctly and accurately for this specific case?
- **Method:** LLM-as-judge

### 7. analyzing_quality
- Did the response analyze the situation correctly — or correctly avoid analyzing when not appropriate?
- **Method:** LLM-as-judge

### 8. followup_quality
- Did the response ask the right follow-up questions — or correctly avoid asking when not needed?
- **Method:** LLM-as-judge

### 9. next_step_quality
- Did the response give the right next steps — or correctly avoid giving steps when not appropriate?
- **Method:** LLM-as-judge

### 10. is_form_referenced
- Did the response reference form/survey data when it should — or correctly avoid it when not relevant?
- **Method:** LLM-as-judge

### 11. sit_e_stance
- Did the response take the right emotional stance? (`reassuring`, `asking_followups`, `flagging_bad_situation`)
- Only meaningful for SIT_E cases; set to `false` on all other types to verify no emotional stance is taken
- **Method:** LLM-as-judge

### 12. is_declined
- Did the response decline when it should — or correctly answer when it should not decline?
- **Method:** LLM-as-judge

---

## Dataset

39 test cases across 8 query types. Managed in `eval/eval_dataset.json`, uploaded to LangSmith via `eval/dataset.py`.

| Type | Cases | Description |
|------|-------|-------------|
| EDU | 6 | Educational questions about agreement concepts |
| BENCH | 4 | Benchmark questions requiring named source citations |
| FORM | 5 | Advice on what to fill into the agreement |
| SIT_A | 5 | Situational analysis — cofounder dynamics |
| SIT_E | 6 | Emotional/relational situations at the agreement creation stage |
| ACT | 4 | Action-oriented questions needing next steps |
| REVIEW | 4 | Review of filled agreement sections |
| GUARD | 5 | Out-of-scope or inappropriate requests |

---

## TODO

### Tone and language quality
- Response does not sound AI-generated (overly formal, structured, or robotic)
- Tone matches the situation (warm for SIT_E, direct for ACT, educational for EDU)
- **Method:** LLM-as-judge
- **Status:** Deferred — implement after core evals are stable

### RAG retrieval quality
- For a given query, is the relevant document in the top k results? (Success@k)
- Does the response use what was retrieved, or ignore it? (grounding)
- **Method:** Success@k programmatic, grounding via LLM-as-judge
- **Status:** Deferred — implement after knowledge base expands to 50+ docs
