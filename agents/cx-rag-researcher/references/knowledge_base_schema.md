# knowledge_base_retrieval_index Schema Reference

**Table:** `mozdata.customer_experience.knowledge_base_retrieval_index`
**Purpose:** Semantic search index over Mozilla Knowledge Base articles, pre-embedded for vector similarity queries.

> LLM-derived columns are prefixed `article_*` on this table (e.g. `article_category_llm`). The prefix differs per source — Kitsune uses `question_*`, Zendesk uses `ticket_*`.
> **The KB table has no language or sentiment LLM columns** — unlike Kitsune/Zendesk there is no `*_language_llm` and no sentiment field, because KB articles are Mozilla-authored, not user content.

## Columns used by the orchestrator

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `title` | STRING | Article title |
| `article_summary_llm` | STRING | LLM-generated summary of the article |
| `article_category_llm` | STRING | LLM-generated high-level category |
| `slug` | STRING | URL slug — maps to `support.mozilla.org/kb/<slug>` |
| `products` | STRING | Products the article applies to |

## Columns available for filtering (not fetched)

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `locale` | STRING | Article language/locale — used by the `locale` filter |
| `last_approved_revision_date` | DATE | Date of the last approved revision — usable for date filtering |
| `embedding` | FLOAT64 REPEATED | Vector for similarity search (`gemini-embedding-001`) |

## Filter coverage

The Knowledge Base table has **no `creation_date` and no `product` (singular) column**. It does have `last_approved_revision_date` (DATE) and `last_updated` (TIMESTAMP) for recency filtering, `products` (STRING) for product scoping, and `locale` for language. Pageview counts (`num_pageviews_last_*`) make article popularity queryable.

## Full schema

| Column | Type | Mode | Description |
|--------|------|------|-------------|
| `id` | INT64 | NULLABLE | Article ID |
| `title` | STRING | NULLABLE | Article title |
| `slug` | STRING | NULLABLE | URL slug — maps to `support.mozilla.org/kb/<slug>` |
| `locale` | STRING | NULLABLE | Article language/locale |
| `content` | STRING | NULLABLE | Full article content |
| `category` | INT64 | NULLABLE | Source category ID (numeric, not a name) |
| `needs_change` | BOOL | NULLABLE | Whether the article is flagged for review |
| `needs_change_comment` | STRING | NULLABLE | Reviewer note about needed changes |
| `share_link` | STRING | NULLABLE | Shareable link for the article |
| `display_order` | INT64 | NULLABLE | Display order within the category |
| `current_revision_id` | INT64 | NULLABLE | ID of the current published revision |
| `latest_localizable_revision_id` | INT64 | NULLABLE | ID of the latest localizable revision |
| `parent_id` | INT64 | NULLABLE | Parent article ID (for localized children) |
| `products` | STRING | NULLABLE | Products the article applies to |
| `topics` | STRING | NULLABLE | Source topic classification |
| `is_template` | BOOL | NULLABLE | Whether the article is a template |
| `is_localizable` | BOOL | NULLABLE | Whether the article can be localized |
| `allow_discussion` | BOOL | NULLABLE | Whether discussions are enabled |
| `last_updated` | TIMESTAMP | NULLABLE | When the article was last updated |
| `last_approved_revision_date` | DATE | NULLABLE | Date of the last approved revision |
| `num_pageviews_last_7_days` | INT64 | NULLABLE | Pageview count over last 7 days |
| `num_pageviews_last_30_days` | INT64 | NULLABLE | Pageview count over last 30 days |
| `num_pageviews_last_90_days` | INT64 | NULLABLE | Pageview count over last 90 days |
| `num_pageviews_last_365_days` | INT64 | NULLABLE | Pageview count over last 365 days |
| `type` | STRING | NULLABLE | Article type |
| `article_summary_llm` | STRING | NULLABLE | LLM-generated summary |
| `article_category_llm` | STRING | NULLABLE | LLM-generated category |
| `article_entities_llm` | STRING | REPEATED | LLM-extracted entities (ARRAY) |
| `article_topics_llm` | STRING | REPEATED | LLM-generated topic tags (ARRAY) |
| `embedding` | FLOAT64 | REPEATED | Vector for similarity search (`gemini-embedding-001`) |
| `metadata` | RECORD | NULLABLE | Pipeline metadata (model/prompt/embedding versions, timestamps, failure reasons) |
| `is_stale` | BOOL | NULLABLE | Whether the article is considered stale |

## Embedding model

All embeddings use `gemini-embedding-001` via Vertex AI. The orchestrator embeds the user's question with the same model at query time — dimensionality must match.

## How VECTOR_SEARCH is used

```sql
SELECT base.title, base.article_summary_llm, base.article_category_llm,
       base.slug, base.products,
       distance, 'knowledge_base' AS _source
FROM VECTOR_SEARCH(
    TABLE `mozdata.customer_experience.knowledge_base_retrieval_index`,
    'embedding',
    (SELECT <query_embedding> AS embedding),
    top_k => 5,
    distance_type => 'COSINE'
)
[WHERE base.locale LIKE '%en-US%']
ORDER BY distance ASC
```

Lower `distance` = more semantically similar to the question.

## Article popularity

Unlike before, KB article popularity **is** queryable via the pageview columns — e.g. rank "most-viewed articles" with `num_pageviews_last_30_days`. This counts article views, which is distinct from how often users *search* for a topic.

## Using the slug field

The `slug` column maps directly to a live article URL:

```
https://support.mozilla.org/kb/<slug>
```

Always include this link when referencing a Knowledge Base article in an answer.
