# kitsune_retrieval_index Schema Reference

**Table:** `mozdata.customer_experience.kitsune_retrieval_index`
**Purpose:** Semantic search index over SUMO forum content, pre-embedded for vector similarity queries.

## Columns used by the orchestrator

| Column | BigQuery Type | Description |
|--------|--------------|-------------|
| `title` | STRING | Original post/question title written by the user |
| `content` | STRING | Full raw text of the post or question |
| `answer_content` | STRING | Accepted or top answer content |
| `question_summary_llm` | STRING | LLM-generated summary of the post |
| `question_category_llm` | STRING | LLM-generated high-level category |
| `question_sentiment_score` | FLOAT64 | User sentiment: -1.0 (very negative) to 1.0 (very positive) — the only trustworthy sentiment signal across all sources |
| `recency_score` | FLOAT64 | Recency weight for ranking |
| `product` | STRING | Firefox product the post relates to |
| `topic` | STRING | Topic classification from SUMO |

## All columns

| Column | Type | Description |
|--------|------|-------------|
| `creation_date` | DATE | When the post was created (partition / date filter) |
| `question_id` | INT64 | Unique question key |
| `answer_id` | INT64 | Accepted answer id (NULL when unanswered) |
| `title` | STRING | Post title |
| `content` | STRING | Full post content |
| `locale` | STRING | Post language/locale |
| `topic` | STRING | SUMO topic classification |
| `tier1_topic` | STRING | Top-level topic tier |
| `tier2_topic` | STRING | Mid-level topic tier |
| `tier3_topic` | STRING | Leaf-level topic tier |
| `answer_content` | STRING | Accepted/top answer text |
| `answer_latency_seconds` | INT64 | Time to accepted answer (NULL = unanswered) |
| `type` | STRING | Post type (single-valued: `question`) |
| `is_self_answer` | BOOL | Whether the asker answered their own question |
| `is_firefox_product` | BOOL | Firefox-product flag (use `product` instead) |
| `num_helpful_votes` | INT64 | Helpful vote count |
| `num_unhelpful_votes` | INT64 | Unhelpful vote count |
| `question_summary_llm` | STRING | LLM-generated summary |
| `question_category_llm` | STRING | LLM-generated category (high-cardinality long tail) |
| `question_language_llm` | STRING | LLM-detected language (prefer `locale`) |
| `question_entities_llm` | ARRAY\<STRING\> | LLM-extracted entities — **array; use `UNNEST`, not `--filter`** |
| `question_topics_llm` | ARRAY\<STRING\> | LLM-generated topic tags — **array; use `UNNEST`, not `--filter`** |
| `question_sentiment_score` | FLOAT64 | Sentiment score -1 to 1 |
| `embedding` | ARRAY\<FLOAT64\> | Vector for similarity search (`gemini-embedding-001`) — never SELECT/display |
| `metadata` | STRUCT | Provenance (model/prompt/embedding versions) — not for analysis |
| `product_version` | STRING | Firefox release (sparse; never for ranking) |
| `product` | STRING | Firefox product |
| `recency_score` | FLOAT64 | Recency weight for ranking |

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
