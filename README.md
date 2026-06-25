# RAG Orchestration Skills

Skills that orchestrate the full RAG pipeline: question → retrieval → BigQuery semantic layer → structured answer.

The retrieval layer is a set of BigQuery tables enriched with LLM-generated categories, topics, embeddings, and sentiment scores. Skills in this repo embed a user's question, retrieve the most relevant context, and synthesize a grounded answer — no hallucination, sources cited.

**Currently implemented for Customer Experience, extensible to other domains.**

## Install

The skills are locked to the read-only **`mozdata.customer_experience`** dataset and authenticate via the `google-auth` library (they never print or handle an access token).

**1. Python packages.** The skill scripts requires the installation of two Python packages:

```bash
pip install google-auth requests
```

- **`google-auth`** — loads your Application Default Credentials and signs each API request, so the scripts never print Google Cloud tokens by invoking `gcloud … print-access-token` nor touch a raw token.
- **`requests`** — the HTTP client used by the `google-auth` session authorized for the BigQuery and Vertex AI REST APIs.

**2. GCP command-line tools.** Set up GCP command line tools, as described on [docs.telemetry.mozilla.org](https://docs.telemetry.mozilla.org/cookbooks/bigquery/access.html#using-the-bq-command-line-tool).

**3. Authenticate (service-account impersonation).** Log in with Application Default Credentials — that's all you set up:

```bash
gcloud auth application-default login
```

> ⚠️ The skills connect using a service account: your authenticated Google Cloud credentials are only used to create a new and temporary access token on behalf of the service account defined in each script's `SERVICE_ACCOUNT` constant, which requires the `roles/iam.serviceAccountTokenCreator` role on that service account.
> Read-only BigQuery (for `query`/`vector-search`) and `cloud-platform` (for `embed`'s Vertex AI) scopes are enforced on the impersonated token in code — which is why your login no longer needs `--scopes`.

The agent may only query **project `mozdata`, dataset `customer_experience`** — any table or view in that dataset, and nothing outside it. The boundary is enforced by asking BigQuery (via a dry run) which tables each query actually reads, so it cannot be evaded by SQL the scripts don't parse.

**4. Install the plugin.**

```bash
/plugin marketplace add https://github.com/mozilla/rag-skills.git
/plugin install rag-skills
```

## Skills

| Skill | Purpose |
|-------|---------|
| `embed` | Embeds a question with `gemini-embedding-001` via Vertex AI |
| `query` | Runs a read-only SQL query for counts, aggregations, rankings, and distributions |
| `vector-search` | Runs `VECTOR_SEARCH` to return the top-K most semantically similar documents |

## Agents

| Agent | Domain | Sources |
|-------|--------|---------|
| `cx-rag-researcher` | Customer Experience | SUMO/Kitsune forums, Zendesk tickets, Mozilla Knowledge Base |

## Running Tests

Unit tests run automatically on every PR via GitHub Actions. To run them locally:

```bash
python -m pytest tests/test_embed.py tests/test_vector_search.py tests/test_query.py -v
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

1. Create `agents/<domain>-rag-researcher.md` — e.g. `agents/customer_experience/report_generator.md`.
   Start the agent file with the frontmatter block (`name`, `description`).
   Add the instructions for the agent and reference the new domain's BigQuery dataset/tables.
2. Modify `skills/query/scripts/query.py` and `skills/vector-search/scripts/vector_search.py` (the `PROJECT`/`DATASET` constants) to enable access to the new domain. Currently locked to `customer_experience`.
3. Register the agent under `agents` in `.claude-plugin/marketplace.json`.
4. Open a PR.
