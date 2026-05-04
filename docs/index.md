# RAG Orchestration Skills

Skills that orchestrate the full RAG pipeline: question → retrieval → BigQuery semantic layer → structured answer.

## What this is

The semantic layer is a set of BigQuery tables enriched with LLM-generated categories, topics, embeddings, and sentiment scores. Skills in this repo embed a user's question, retrieve the most relevant context, and synthesize a grounded answer — no hallucination, sources cited.

**Current skills:**

- **[cx-rag-researcher](skills/overview.md)** — Customer Experience: SUMO/Kitsune forums, Zendesk tickets, Mozilla Knowledge Base

## Install

```bash
/plugin marketplace add https://github.com/mozilla/rag-skills.git
/plugin install rag-skills
```

## Quick example

> *What are users saying about Firefox sync in Q1 2026?*

Claude embeds the question, retrieves context from the CX semantic layer, and returns a grounded answer — no fabrication, sources cited.
