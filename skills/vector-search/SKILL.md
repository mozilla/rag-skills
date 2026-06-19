---
name: vector-search
description: Runs VECTOR_SEARCH against the Customer Experience retrieval indexes (mozdata.customer_experience) and returns the top-K most semantically similar documents. Use after the embed skill has produced an embedding file.
---

# Vector Search Skill

Queries a Customer Experience retrieval index using a pre-computed embedding vector and returns the closest matching documents via cosine similarity.

This skill is locked to **`mozdata.customer_experience`** — it can read any table or view in that dataset, and anything outside it is rejected (enforced via a BigQuery dry run that resolves the tables the query actually reads). Table and column names must be plain identifiers; columns that don't exist are rejected by BigQuery. The embedding, dates, and filter values are passed as typed query parameters (never interpolated into SQL).

## Authentication

Read-only BigQuery access only — authenticate with the read-only scope:

```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/bigquery.readonly
```

(The `embed` skill needs Vertex AI — append `,https://www.googleapis.com/auth/cloud-platform` so one login covers both.)

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/vector-search/scripts/vector_search.py \
  --embedding-file /tmp/embedding.json \
  --table mozdata.customer_experience.<index> \
  [--embedding-column embedding] \
  [--columns col1,col2,...] \
  [--label "Display Name"] \
  [--date-column COLUMN] \
  [--s YYYY-MM-DD] [--e YYYY-MM-DD] \
  [--filter column:value] \
  [--top-k 5]
```

`<index>` is any table or view in `mozdata.customer_experience`; the retrieval indexes are `kitsune_retrieval_index`, `zendesk_retrieval_index`, and `knowledge_base_retrieval_index`.

## Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--embedding-file` | yes | Path to the JSON embedding file produced by the `embed` skill |
| `--table` | yes | A table or view in `mozdata.customer_experience` (bare table name also accepted; resolved to the locked project/dataset) |
| `--embedding-column` | no | Name of the embedding column (default: `embedding`) |
| `--columns` | no | Comma-separated columns to return (default: all). Must be plain identifiers that exist in the table |
| `--label` | no | Display name for the results header (default: table name) |
| `--date-column` | no | Column to apply `--s` / `--e` date filters against (e.g. `creation_date`) |
| `--s` | no | Start date filter `YYYY-MM-DD` (requires `--date-column`) |
| `--e` | no | End date filter `YYYY-MM-DD` (requires `--date-column`) |
| `--filter` | no | Partial-match filter as `column:value`. Repeatable. Scalar columns only |
| `--top-k` | no | Number of results to return (default: 5) |

## Output

Formatted context block printed to stdout:

```
=== Display Name (5 results) ===
[1]
column_a: value
column_b: value
distance: 0.28
...
```

## Typical workflow with the embed skill

```bash
# Step 1 — embed the question
python ${CLAUDE_PLUGIN_ROOT}/skills/embed/scripts/embed.py \
  --question "What are users saying about Firefox sync?" \
  > /tmp/embedding.json

# Step 2 — search a CX index
python ${CLAUDE_PLUGIN_ROOT}/skills/vector-search/scripts/vector_search.py \
  --embedding-file /tmp/embedding.json \
  --table mozdata.customer_experience.kitsune_retrieval_index \
  --columns title,content,question_summary_llm,question_sentiment_score,product,topic \
  --label "SUMO / Kitsune" \
  --date-column creation_date \
  --s 2026-01-01 --e 2026-03-31 \
  --filter "product:Fenix" \
  --filter "locale:es"
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Authentication rejected (401)` / `GCP authentication required` | Run `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/bigquery.readonly` |
| `Missing dependency` | `pip install google-auth requests` |
| `Table not allowed` / `Invalid column` | Use a table or view in `mozdata.customer_experience` and plain column identifiers that exist in it |
| `Failed to read embedding file` | Check the path; ensure `embed` skill ran successfully |
| `Invalid --filter format` | Use `column:value` — no spaces around the colon |
| `No results found` | Broaden date range, remove filters, or increase `--top-k` |
