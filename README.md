# RAG Orchestration Skills

Claude Code skills that orchestrate the full RAG pipeline: question → retrieval → BigQuery semantic layer → structured answer.

The semantic layer is a set of BigQuery tables enriched with LLM-generated categories, topics, embeddings, and sentiment scores. Skills in this repo embed a user's question, retrieve the most relevant context, and synthesize a grounded answer — no hallucination, sources cited.

**Customer Experience first. Extensible to any domain with a semantic layer in BigQuery.**

## Install

```bash
/plugin marketplace add https://github.com/mozilla/rag-skills.git
/plugin install rag-skills
```

## Skills

| Skill | Domain | Sources |
|-------|--------|---------|
| `cx-rag-researcher` | Customer Experience | SUMO/Kitsune forums, Zendesk tickets, Mozilla Knowledge Base |

## Prerequisites

Requires Google Cloud credentials to query BigQuery:

```bash
gcloud auth application-default login
gcloud config set project <project-name-from-DE>
```

## Local Development

```bash
./scripts/dev-setup.sh        # symlink skills for local testing
./scripts/dev-setup.sh --clean  # remove symlinks
```

## Adding a New Domain

1. Create `skills/<domain>-rag/SKILL.md` with frontmatter (`name`, `description`) and orchestration instructions.
2. Add optional `scripts/orchestrator.py` for retrieval logic.
3. Register in `.claude-plugin/marketplace.json` under `skills`.
4. Commit and push to main.
