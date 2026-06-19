# knowledge_base_retrieval_index Schema Reference

**Table:** `mozdata.customer_experience.knowledge_base_retrieval_index`
**Purpose:** Semantic search index over Mozilla Knowledge Base articles, pre-embedded for vector similarity queries.

## Columns used by the orchestrator

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `title` | STRING | Article title |
| `article_summary_llm` | STRING | LLM-generated summary of the article |
| `article_category_llm` | STRING | LLM-generated high-level category |
| `slug` | STRING | URL slug — maps to `support.mozilla.org/kb/<slug>` |

## Columns available for filtering (not fetched)

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `locale` | STRING | Article language/locale — KB is multilingual; filter `locale = 'en-US'` for English |
| `products` | STRING | Slash-delimited product slugs (e.g. `/firefox/mobile/`) — match with `LIKE '%/firefox/%'` |
| `embedding` | ARRAY\<FLOAT64\> | Vector for similarity search (`gemini-embedding-001`) |

## Filter coverage

The Knowledge Base table has **no `creation_date` and no `product` column**. For a date bound use `last_approved_revision_date` (DATE). For product, filter the `products` slug string with `LIKE`. There is **no sentiment column** on KB.

## Full schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT64 | Article ID |
| `title` | STRING | Article title |
| `slug` | STRING | URL slug — `support.mozilla.org/kb/<slug>` |
| `locale` | STRING | Article language/locale (52 locales) |
| `content` | STRING | Article body text (~22% empty) |
| `category` | INT64 | Opaque category id (use `article_category_llm`) |
| `needs_change` | BOOL | Editorial review flag |
| `needs_change_comment` | STRING | Editorial review note |
| `share_link` | STRING | Shareable link (sparse; prefer building from `slug`) |
| `display_order` | INT64 | UI ordering — not analytical |
| `current_revision_id` | INT64 | Current published revision id |
| `latest_localizable_revision_id` | INT64 | Latest localizable revision id |
| `parent_id` | INT64 | Parent article id (currently all-NULL — re-check before use) |
| `products` | STRING | Slash-delimited product slugs — filter with `LIKE '%/slug/%'`, do not `UNNEST` |
| `topics` | STRING | Slash-delimited topic slugs (~26% empty) — same `LIKE` pattern |
| `is_template` | BOOL | Template flag |
| `is_localizable` | BOOL | Localizable flag |
| `allow_discussion` | BOOL | Discussions enabled (near-constant) |
| `last_updated` | TIMESTAMP | Last edit timestamp |
| `last_approved_revision_date` | DATE | Date of last approved revision (the only date bound for KB) |
| `num_pageviews_last_7_days` | INT64 | Pageviews, last 7 days |
| `num_pageviews_last_30_days` | INT64 | Pageviews, last 30 days |
| `num_pageviews_last_90_days` | INT64 | Pageviews, last 90 days |
| `num_pageviews_last_365_days` | INT64 | Pageviews, last 365 days |
| `type` | STRING | Article type (single-valued: `article`) |
| `article_summary_llm` | STRING | LLM-generated summary |
| `article_category_llm` | STRING | LLM-generated category (high-cardinality long tail) |
| `article_entities_llm` | ARRAY\<STRING\> | LLM-extracted entities — **array; use `UNNEST`, not `--filter`** |
| `article_topics_llm` | ARRAY\<STRING\> | LLM-generated topic tags — **array; use `UNNEST`, not `--filter`** |
| `embedding` | ARRAY\<FLOAT64\> | Vector for similarity search (`gemini-embedding-001`) — never SELECT/display |
| `metadata` | STRUCT | Provenance (model/prompt/embedding versions) — not for analysis |
| `is_stale` | BOOL | Staleness flag (~70% true) — surface when citing KB as current guidance |

## Embedding model

All embeddings use `gemini-embedding-001` via Vertex AI. The orchestrator embeds the user's question with the same model at query time — dimensionality must match.

## How VECTOR_SEARCH is used

```sql
SELECT base.title, base.article_summary_llm, base.article_category_llm,
       base.slug, distance
FROM VECTOR_SEARCH(
    TABLE `mozdata.customer_experience.knowledge_base_retrieval_index`,
    'embedding',
    (SELECT <query_embedding> AS embedding),
    top_k => 5,
    distance_type => 'COSINE'
)
[WHERE LOWER(base.locale) = 'en-us']
ORDER BY distance ASC
```

Lower `distance` = more semantically similar to the question.

## Using the slug field

The `slug` column maps directly to a live article URL:

```
https://support.mozilla.org/kb/<slug>
```

Always include this link when referencing a Knowledge Base article in an answer.
