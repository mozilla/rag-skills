---
name: query
description: Runs a direct SQL query against any BigQuery table and returns results as a formatted table. Use when the question requires counts, aggregations, rankings, or distributions — not when it requires reading document text. Reference tables by their full name (e.g. mozdata.customer_experience.kitsune_retrieval_index).
---

# Query Skill

Runs a direct SQL query against BigQuery and prints results as a formatted text table. No embedding required.

## Usage

```bash
python "${CLAUDE_PLUGIN_ROOT:?set by the plugin system; if empty, invoke this via the Skill tool}"/skills/query/scripts/query.py \
  --sql "<SQL querying mozdata.customer_experience.<table>>"
```

Reference tables by their full name, e.g. `mozdata.customer_experience.kitsune_retrieval_index`.

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
- Zendesk: `creation_date` TIMESTAMP — use `DATE(creation_date) BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'`
- Knowledge Base: no date column

```sql
-- Top topics by volume (Kitsune)
SELECT topic, COUNT(*) AS count
FROM `mozdata.customer_experience.kitsune_retrieval_index`
WHERE creation_date BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY topic ORDER BY count DESC LIMIT 10

-- Top categories by volume (Zendesk)
SELECT category_generated, COUNT(*) AS count
FROM `mozdata.customer_experience.zendesk_retrieval_index`
WHERE DATE(creation_date) BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY category_generated ORDER BY count DESC LIMIT 10

-- Average sentiment by topic (Kitsune only — do not use Zendesk sentiment)
SELECT topic, COUNT(*) AS count, ROUND(AVG(sentiment_score), 2) AS avg_sentiment
FROM `mozdata.customer_experience.kitsune_retrieval_index`
WHERE creation_date BETWEEN '2026-03-24' AND '2026-04-22'
GROUP BY topic ORDER BY avg_sentiment ASC LIMIT 10

-- Volume by product (Zendesk)
SELECT product, COUNT(*) AS count
FROM `mozdata.customer_experience.zendesk_retrieval_index`
WHERE DATE(creation_date) BETWEEN '2026-03-24' AND '2026-04-22'
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
| `Authentication rejected (401)` | Run `gcloud auth application-default login` |
| `No GCP project configured` | Run `gcloud config set project <project-id>` |
| `API error` | Confirm the project name with DE and re-authenticate |
| `No results` | Check date range, table name, and filter values |
