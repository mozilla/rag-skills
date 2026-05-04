---
name: vector-search
description: Runs VECTOR_SEARCH against any BigQuery table that has an embedding column. Returns the top-K most semantically similar documents. Use after the embed skill has produced an embedding file. The caller is responsible for supplying the table reference, columns, and any filters.
---

# Vector Search Skill

Queries any BigQuery table using a pre-computed embedding vector and returns the closest matching documents via cosine similarity.

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/vector-search/scripts/vector_search.py \
  --embedding-file /tmp/embedding.json \
  --table dataset.table_name \
  [--embedding-column embedding] \
  [--columns col1,col2,...] \
  [--label "Display Name"] \
  [--date-column COLUMN] \
  [--s YYYY-MM-DD] [--e YYYY-MM-DD] \
  [--filter column:value] \
  [--top-k 5]
```

## Arguments

| Flag | Required | Description |
|------|----------|-------------|
| `--embedding-file` | yes | Path to the JSON embedding file produced by the `embed` skill |
| `--table` | yes | BigQuery table as `dataset.table` (project from gcloud) or `project.dataset.table` |
| `--embedding-column` | no | Name of the embedding column (default: `embedding`) |
| `--columns` | no | Comma-separated columns to return (default: all columns) |
| `--label` | no | Display name for the results header (default: table name) |
| `--date-column` | no | Column to apply `--s` / `--e` date filters against |
| `--s` | no | Start date filter `YYYY-MM-DD` (requires `--date-column`) |
| `--e` | no | End date filter `YYYY-MM-DD` (requires `--date-column`) |
| `--filter` | no | Partial-match filter as `column:value`. Repeatable. |
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

# Step 2 — search a table
python ${CLAUDE_PLUGIN_ROOT}/skills/vector-search/scripts/vector_search.py \
  --embedding-file /tmp/embedding.json \
  --table my_dataset.my_index_table \
  --columns title,content,created_at \
  --label "My Source" \
  --date-column created_at \
  --s 2026-01-01 --e 2026-03-31 \
  --filter "product:Firefox" \
  --filter "locale:es"
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Authentication rejected (401)` | Run `gcloud auth application-default login` |
| `No GCP project configured` | Run `gcloud config set project <project-id>` |
| `Failed to read embedding file` | Check the path; ensure `embed` skill ran successfully |
| `Invalid --filter format` | Use `column:value` — no spaces around the colon |
| `No results found` | Broaden date range, remove filters, or increase `--top-k` |
