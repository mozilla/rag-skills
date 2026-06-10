# kitsune_retrieval_index Schema Reference

**Table:** `mozdata.customer_experience.kitsune_retrieval_index`
**Purpose:** Semantic search index over SUMO forum content, pre-embedded for vector similarity queries.

> LLM-derived columns are prefixed `question_*` on this table (e.g. `question_category_llm`). The prefix differs per source — Zendesk uses `ticket_*`, Knowledge Base uses `article_*`.

## Columns used by the orchestrator

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `title` | STRING | Original post/question title written by the user |
| `content` | STRING | Full raw text of the post or question |
| `answer_content` | STRING | Accepted or top answer content |
| `question_summary_llm` | STRING | LLM-generated summary of the post |
| `question_category_llm` | STRING | LLM-generated high-level category |
| `question_sentiment_score` | FLOAT64 | User sentiment: -1.0 (very negative) to 1.0 (very positive) |
| `recency_score` | FLOAT64 | Recency weight for ranking |
| `product` | STRING | Firefox product the post relates to |
| `topic` | STRING | Topic classification from SUMO |

## All columns

| Column | Type | Mode | Description |
|--------|------|------|-------------|
| `creation_date` | DATE | NULLABLE | When the post was created |
| `question_id` | INT64 | NULLABLE | SUMO question identifier |
| `answer_id` | INT64 | NULLABLE | SUMO answer identifier |
| `title` | STRING | NULLABLE | Post title |
| `content` | STRING | NULLABLE | Full post content |
| `locale` | STRING | NULLABLE | Post language/locale |
| `topic` | STRING | NULLABLE | SUMO topic classification |
| `tier1_topic` | STRING | NULLABLE | Top-level topic tier |
| `tier2_topic` | STRING | NULLABLE | Mid-level topic tier |
| `tier3_topic` | STRING | NULLABLE | Leaf-level topic tier |
| `answer_content` | STRING | NULLABLE | Top answer text |
| `answer_latency_seconds` | INT64 | NULLABLE | Seconds between question and accepted answer |
| `type` | STRING | NULLABLE | Post type |
| `is_self_answer` | BOOL | NULLABLE | Whether the asker answered their own question |
| `is_firefox_product` | BOOL | NULLABLE | Whether the post relates to a Firefox product |
| `num_helpful_votes` | INT64 | NULLABLE | Helpful vote count |
| `num_unhelpful_votes` | INT64 | NULLABLE | Unhelpful vote count |
| `question_summary_llm` | STRING | NULLABLE | LLM-generated summary |
| `question_category_llm` | STRING | NULLABLE | LLM-generated category |
| `question_language_llm` | STRING | NULLABLE | LLM-detected language |
| `question_entities_llm` | STRING | REPEATED | LLM-extracted entities (ARRAY) |
| `question_topics_llm` | STRING | REPEATED | LLM-generated topic tags (ARRAY) |
| `question_sentiment_score` | FLOAT64 | NULLABLE | Sentiment score -1 to 1 |
| `embedding` | FLOAT64 | REPEATED | Vector for similarity search (`gemini-embedding-001`) |
| `metadata` | RECORD | NULLABLE | Pipeline metadata (model/prompt/embedding versions, timestamps, failure reasons) |
| `product_version` | STRING | NULLABLE | Product version associated with the post |
| `product` | STRING | NULLABLE | Firefox product |
| `recency_score` | FLOAT64 | NULLABLE | Recency weight for ranking |

## Embedding model

All embeddings use `gemini-embedding-001` via Vertex AI. The orchestrator embeds the user's question with the same model at query time — dimensionality must match.

## How VECTOR_SEARCH is used

```sql
SELECT base.<content_cols>, distance
FROM VECTOR_SEARCH(
    TABLE `mozdata.customer_experience.kitsune_retrieval_index`,
    'embedding',
    (SELECT <query_embedding> AS embedding),
    top_k => 5,
    distance_type => 'COSINE'
)
ORDER BY distance ASC
```

Lower `distance` = more semantically similar to the question.
