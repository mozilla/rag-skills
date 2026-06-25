---
name: query
description: Runs a read-only SQL query against the Customer Experience tables (mozdata.customer_experience) and returns results as a formatted table. Use when the question requires counts, aggregations, rankings, or distributions — not when it requires reading document text.
---

# Query Skill

Runs a read-only SQL query against BigQuery and prints results as a formatted text table. No embedding required.

This skill is locked to **`mozdata.customer_experience`** — it can read any table or view in that dataset, and anything outside it is rejected. Only a single read-only `SELECT` (optionally `WITH … SELECT`) is accepted. The dataset boundary is enforced by asking BigQuery (via a dry run) which tables the query actually reads, so it can't be evaded by SQL the script doesn't parse.

## Authentication

This skill connects to BigQuery using a service account — read-only access is enforced on the impersonated token. Just log in:

```bash
gcloud auth application-default login
```

Your authenticated BigQuery credentials are only used to create a new and temporary read-only access token on behalf of the service account defined in `SERVICE_ACCOUNT`, which requires the `roles/iam.serviceAccountTokenCreator` role on that service account. Your login no longer needs `--scopes`.

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/query/scripts/query.py \
  --sql "<read-only SELECT over mozdata.customer_experience.<table>>"
```

Reference tables by their fully-qualified name (`mozdata.customer_experience.<table>`).

## When to use

Use this skill instead of `embed` + `vector-search` when the question requires:
- Counts ("how many tickets about X?")
- Rankings ("top N topics by volume")
- Distributions ("ticket count by product")
- Aggregations ("average sentiment by category")
- Any answer that is a number, ranked list, or summary statistic

Use `embed` + `vector-search` when the question requires reading and synthesizing document text.

## Common SQL patterns

**Dataset:** `mozdata.customer_experience`
**Tables:** `kitsune_retrieval_index`, `zendesk_retrieval_index`, `knowledge_base_retrieval_index`

**Date filter columns:**
- Kitsune: `creation_date` DATE — use `creation_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`
- Zendesk: `creation_date` DATE — use `creation_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`
- Knowledge Base: no `creation_date`; use `last_approved_revision_date` (DATE) if a date bound is needed

```sql
-- Top topics by volume (Kitsune)
SELECT topic, COUNT(*) AS count
FROM `mozdata.customer_experience.kitsune_retrieval_index`
WHERE creation_date BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY topic ORDER BY count DESC LIMIT 10

-- Top categories by volume (Zendesk)
SELECT ticket_category_llm, COUNT(*) AS count
FROM `mozdata.customer_experience.zendesk_retrieval_index`
WHERE creation_date BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY ticket_category_llm ORDER BY count DESC LIMIT 10

-- Average sentiment by topic (Kitsune only — do not use Zendesk sentiment)
SELECT topic, COUNT(*) AS count, ROUND(AVG(question_sentiment_score), 2) AS avg_sentiment
FROM `mozdata.customer_experience.kitsune_retrieval_index`
WHERE creation_date BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY topic ORDER BY avg_sentiment ASC LIMIT 10

-- Volume by product (Zendesk)
SELECT product, COUNT(*) AS count
FROM `mozdata.customer_experience.zendesk_retrieval_index`
WHERE creation_date BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY product ORDER BY count DESC
```

## Output

A plain-text formatted table:

```
topic          count
-------------  -----
site-breakage  142
sync           98
passwords      74
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Authentication rejected (401)` / `GCP authentication required` | Re-run `gcloud auth application-default login`; confirm you have `roles/iam.serviceAccountTokenCreator` on the service account in `SERVICE_ACCOUNT` |
| `Missing dependency` | `pip install google-auth requests` |
| `Refusing to run … outside the allowed dataset` / `Only read-only SELECT` | Query only tables or views in `mozdata.customer_experience` with a single read-only SELECT |
| `No results` | Check date range, table name, and filter values |
