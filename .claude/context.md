---
name: Current session context
saved: Wed Mar 25 11:56:47 PDT 2026
description: What was being worked on at the end of the last session — resume point for next session
type: project
---

## Session Summary

### What we worked on

**RAG underusage and score threshold investigation**

Problem: The agent wasn't calling `rag_search` for domain-specific questions (e.g. "how do people generally split equity" got answered from model knowledge with no tool call). Two root causes identified:

1. **Claude not deciding to search** — the `<tools>` prompt was too passive ("search when related"). Fixed by making it directive: "search before answering any domain-specific question, don't rely on general knowledge when grounded guidance is available."

2. **Score threshold miscalibration** — scores were compressing into 0.65–0.90 regardless of relevance because:
   - High-dimensional vector spaces (1536 dims) cause cosine similarity scores to cluster (concentration of measure)
   - Domain-specific KB means all docs live in the same semantic neighborhood — no "far away" documents to create score spread

### Decisions made

- **`top_k`**: Set to 100 (Pinecone's max) — effectively "return all docs" so the threshold does the filtering, not an arbitrary top-k cap
- **Score threshold**: Set to 0.80 in `agent/tools.py` — cuts out weak matches while keeping relevant ones. 0.75 is noise for this KB; 0.80 is the practical signal floor
- **Prompt**: `<tools>` section updated to be directive about when to search

### State of changes

All changes made but **not yet committed or pushed**:
- `agent/tools.py` — top_k=100, score threshold 0.80
- `prompts/advisor_prompt.py` — `<tools>` section rewritten
- `CLAUDE.md` — stack section updated to reflect top-k=100, threshold 0.80

### Next steps

1. **Test the RAG changes** — run the local server and ask a domain-specific question (e.g. "how do people split equity?") — verify a `rag_search` tool call appears in LangSmith traces
2. **Check the score key** — confirm Pinecone returns scores under `_score` key (the threshold filter uses `h.get("_score", 0)`) — if it's a different key, filter won't work silently
3. **Commit and push** the RAG + prompt changes
4. **Address remaining items from the prompt review list** (from earlier this session):
   - Fix broken sentence in `<response_format>` item 1
   - Add back `<conversation_rules>` (removed at some point, was in Tim's version)
   - Add empty survey handling guidance
   - Mental health / distress guardrails (flagged as P1 in CLAUDE.md)
   - Merge `<caution>` / `<core_approach>` overlap on "ask for context before acting"
