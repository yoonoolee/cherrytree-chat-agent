---
name: Current session context
saved: Mon Mar 23 22:39:19 PDT 2026
description: What was being worked on at the end of the last session — resume point for next session
type: project
---

## Where we left off

Discussing the RAG scoring problem. The concern: even gibberish queries score ~0.75 against documents in Pinecone. The current 0.7 score threshold in `agent/tools.py` is meaningless — dense embeddings always map any input to somewhere in the vector space, so scores are compressed into a narrow band (0.6–0.85) regardless of actual relevance. The threshold provides false precision and filters almost nothing.

The decision on how to address this was **not made** — session ended before resolving it. Current code still has `score < 0.7` threshold and `top_k: 3` in `agent/tools.py`. Pick up the discussion fresh next session.
