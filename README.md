# RAG Orchestration Skills

Skills that orchestrate the full RAG pipeline: question → retrieval → BigQuery semantic layer → structured answer.

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

## Running Tests

Unit tests run automatically on every PR via GitHub Actions. To run them locally:

```bash
python -m pytest tests/test_embed.py tests/test_vector_search.py -v
```

## Contributing Changes to the cx-rag-researcher Agent

If you modify `agents/cx-rag-researcher.md`, you must run the golden set evaluation before opening a PR.

**Step 1 — Run all test questions through the agent:**
```bash
python tests/golden_set/run_agent.py
```

**Step 2 — Evaluate the responses with the LLM judge:**
```bash
python tests/golden_set/evaluate.py
```

**Step 3 — Commit the report with your PR:**
```bash
git add tests/golden_set/report.json
```

GitHub Actions will verify the report exists and all questions passed. PRs with failures will be blocked.

## Adding a New Domain

1. Create `skills/<domain>-rag/SKILL.md` with frontmatter (`name`, `description`) and orchestration instructions.
2. Add optional `scripts/orchestrator.py` for retrieval logic.
3. Register in `.claude-plugin/marketplace.json` under `skills`.
4. Commit and push to main.
