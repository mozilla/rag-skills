# zendesk_retrieval_index Schema Reference

**Table:** `mozdata.customer_experience.zendesk_retrieval_index`
**Purpose:** Semantic search index over Zendesk support tickets, pre-embedded for vector similarity queries.

## Columns used by the orchestrator

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `title` | STRING | Ticket subject or title |
| `content` | STRING | Full ticket body text |
| `ticket_summary_llm` | STRING | LLM-generated summary of the ticket |
| `ticket_category_llm` | STRING | LLM-generated high-level category (Zendesk's main topic/category signal) |
| `ticket_sentiment_score` | FLOAT64 | Sentiment score -1.0 to 1.0 — **not reliable as a user-sentiment signal; use Kitsune `question_sentiment_score` for sentiment** |
| `product` | STRING | Firefox product the ticket relates to (no Firefox Desktop tickets) |
| `star_rating` | STRING | Star rating for the support interaction (`5star`…`1star`; mostly empty) |
| `recency_score` | FLOAT64 | Recency weight for ranking |

## Columns available for filtering (not fetched)

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `creation_date` | DATE | When the ticket was created — used by `--s` / `--e` date filters |
| `locale` | STRING | Ticket language/locale — used by `--filter "locale:<code>"` |
| `embedding` | ARRAY\<FLOAT64\> | Vector for similarity search (`gemini-embedding-001`) |

## Full schema

| Column | Type | Description |
|--------|------|-------------|
| `creation_date` | DATE | When the ticket was created (partition / date filter) |
| `ticket_id` | INT64 | Unique ticket key |
| `title` | STRING | Ticket subject or title |
| `content` | STRING | Full ticket body text |
| `status` | STRING | Ticket status (~97% `closed` — weak signal) |
| `last_solved_at` | TIMESTAMP | When the ticket was last solved |
| `closed_at` | TIMESTAMP | When the ticket was closed |
| `resolution_latency_seconds` | INT64 | Time to resolution (NULL = unresolved) |
| `star_rating` | STRING | User-provided star rating (`5star`…`1star`; ~74% empty) |
| `locale` | STRING | Ticket language/locale |
| `custom_country` | STRING | Country (sparse) |
| `group_name` | STRING | Support group that handled the ticket |
| `via_channel` | STRING | Channel through which the ticket was submitted |
| `custom_category` | STRING | Support tag (`accounts`/`technical`/`payment`…; sparse) |
| `automation_category` | INT64 | Opaque automation flag — avoid |
| `type` | STRING | Ticket type (single-valued: `ticket`) |
| `ticket_summary_llm` | STRING | LLM-generated summary |
| `ticket_category_llm` | STRING | LLM-generated category (high-cardinality long tail) |
| `ticket_language_llm` | STRING | LLM-detected language (prefer `locale`) |
| `ticket_entities_llm` | ARRAY\<STRING\> | LLM-extracted entities — **array; use `UNNEST`, not `--filter`** |
| `ticket_topics_llm` | ARRAY\<STRING\> | LLM-generated topic tags (Zendesk's topic signal) — **array; use `UNNEST`, not `--filter`** |
| `ticket_sentiment_score` | FLOAT64 | Sentiment score -1 to 1 — **do not use** (unreliable for Zendesk) |
| `embedding` | ARRAY\<FLOAT64\> | Vector for similarity search (`gemini-embedding-001`) — never SELECT/display |
| `metadata` | STRUCT | Provenance (model/prompt/embedding versions) — not for analysis |
| `product_version` | STRING | App-version string (~97% empty; not Firefox releases) — unusable |
| `product` | STRING | Firefox product the ticket relates to |
| `recency_score` | FLOAT64 | Recency weight for ranking |

## Embedding model

All embeddings use `gemini-embedding-001` via Vertex AI. The orchestrator embeds the user's question with the same model at query time — dimensionality must match.

## How VECTOR_SEARCH is used

```sql
SELECT base.title, base.ticket_summary_llm, base.ticket_category_llm,
       base.product, base.star_rating, base.recency_score, distance
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

- **Use for:** what bugs/problems users report, ticket volume by category, product-specific issue patterns.
- **Do not use for:** sentiment — `ticket_sentiment_score` does not reliably reflect user sentiment. Use Kitsune `question_sentiment_score` instead.
- **`star_rating`** reflects satisfaction with the support interaction, not with the Firefox product itself.
