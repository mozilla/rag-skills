# zendesk_retrieval_index Schema Reference

**Table:** `mozdata.customer_experience.zendesk_retrieval_index`
**Purpose:** Semantic search index over Zendesk support tickets, pre-embedded for vector similarity queries.

> LLM-derived columns are prefixed `ticket_*` on this table (e.g. `ticket_category_llm`). The prefix differs per source — Kitsune uses `question_*`, Knowledge Base uses `article_*`.
> **`creation_date` is a `DATE`** (not a TIMESTAMP) — filter with `creation_date BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'` directly, no `DATE(...)` wrapper needed.

## Columns used by the orchestrator

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `title` | STRING | Ticket subject or title |
| `content` | STRING | Full ticket body text |
| `ticket_summary_llm` | STRING | LLM-generated summary of the ticket |
| `ticket_category_llm` | STRING | LLM-generated high-level category |
| `ticket_sentiment_score` | FLOAT64 | Sentiment score -1.0 to 1.0 — **not reliable as a user sentiment signal; use Kitsune for sentiment analysis** |
| `product` | STRING | Firefox product the ticket relates to |
| `star_rating` | STRING | User-provided star rating for the support interaction |
| `recency_score` | FLOAT64 | Recency weight for ranking |

## Columns available for filtering (not fetched)

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `creation_date` | DATE | When the ticket was created — used by date-range filters (`creation_date BETWEEN ...`) |
| `locale` | STRING | Ticket language/locale — used by the `locale` filter |
| `custom_category` | STRING | Source-assigned category (human/system, not LLM) |
| `embedding` | FLOAT64 REPEATED | Vector for similarity search (`gemini-embedding-001`) |

## Full schema

| Column | Type | Mode | Description |
|--------|------|------|-------------|
| `creation_date` | DATE | NULLABLE | When the ticket was created |
| `ticket_id` | INT64 | NULLABLE | Zendesk ticket identifier |
| `title` | STRING | NULLABLE | Ticket subject or title |
| `content` | STRING | NULLABLE | Full ticket body text |
| `status` | STRING | NULLABLE | Ticket status (e.g. solved, closed, open) |
| `last_solved_at` | TIMESTAMP | NULLABLE | When the ticket was most recently solved |
| `closed_at` | TIMESTAMP | NULLABLE | When the ticket was closed |
| `resolution_latency_seconds` | INT64 | NULLABLE | Seconds from creation to resolution |
| `star_rating` | STRING | NULLABLE | User-provided star rating for the support interaction |
| `locale` | STRING | NULLABLE | Ticket language/locale |
| `custom_country` | STRING | NULLABLE | Source-assigned country |
| `group_name` | STRING | NULLABLE | Support group that handled the ticket |
| `via_channel` | STRING | NULLABLE | Channel through which the ticket was submitted |
| `custom_category` | STRING | NULLABLE | Source-assigned category (not LLM) |
| `automation_category` | INT64 | NULLABLE | Automation-assigned category tag (numeric) |
| `type` | STRING | NULLABLE | Ticket type |
| `ticket_summary_llm` | STRING | NULLABLE | LLM-generated summary |
| `ticket_category_llm` | STRING | NULLABLE | LLM-generated category |
| `ticket_language_llm` | STRING | NULLABLE | LLM-detected language |
| `ticket_entities_llm` | STRING | REPEATED | LLM-extracted entities (ARRAY) |
| `ticket_topics_llm` | STRING | REPEATED | LLM-generated topic tags (ARRAY) |
| `ticket_sentiment_score` | FLOAT64 | NULLABLE | Sentiment score -1 to 1 (not reliable for user sentiment) |
| `embedding` | FLOAT64 | REPEATED | Vector for similarity search (`gemini-embedding-001`) |
| `metadata` | RECORD | NULLABLE | Pipeline metadata (model/prompt/embedding versions, timestamps, failure reasons) |
| `product_version` | STRING | NULLABLE | Product version associated with the ticket |
| `product` | STRING | NULLABLE | Firefox product the ticket relates to |
| `recency_score` | FLOAT64 | NULLABLE | Recency weight for ranking |

## Embedding model

All embeddings use `gemini-embedding-001` via Vertex AI. The orchestrator embeds the user's question with the same model at query time — dimensionality must match.

## How VECTOR_SEARCH is used

```sql
SELECT base.title, base.ticket_summary_llm, base.ticket_category_llm,
       base.ticket_sentiment_score, base.product, base.star_rating, base.recency_score,
       distance, 'zendesk' AS _source
FROM VECTOR_SEARCH(
    TABLE `mozdata.customer_experience.zendesk_retrieval_index`,
    'embedding',
    (SELECT <query_embedding> AS embedding),
    top_k => 5,
    distance_type => 'COSINE'
)
[WHERE base.creation_date >= '...' AND ...]
ORDER BY distance ASC
```

Lower `distance` = more semantically similar to the question.

## Interpreting Zendesk results

- **Use for:** Understanding what bugs or problems users are reporting, ticket volume by category, product-specific issue patterns.
- **Do not use for:** Sentiment analysis — `ticket_sentiment_score` here does not reliably reflect user sentiment. Use Kitsune `question_sentiment_score` instead.
- **`star_rating`** reflects user satisfaction with the support interaction, not with the Firefox product itself.
- **Categories:** `ticket_category_llm` is the LLM-assigned category; `custom_category` is source-assigned.
