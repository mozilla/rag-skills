# Changelog

## [1.1.0] - 2026-06-19

### Security
- Token-free authentication: skills now authenticate via the `google-auth` library (Application Default Credentials) and never invoke `gcloud … print-access-token` or read, print, or store a raw access token.
- Least-privilege scopes: `query` and `vector-search` request the read-only `bigquery.readonly` scope; `embed` uses `cloud-platform` (required for Vertex AI).
- Dataset lock: skills are restricted to the read-only `mozdata.customer_experience` dataset, enforced authoritatively by a BigQuery dry run that resolves every referenced table (covers CTEs, subqueries, joins, and views).
- Read-only SQL guard: `query` accepts only single-statement `SELECT`/`WITH` queries; writes and DDL are rejected.
- Prompt-injection defense: the `cx-rag-researcher` agent treats all retrieved content as untrusted data, never as instructions.

### Added
- Unit tests for the `query` SELECT-only and dataset-scope guards, and a schema snapshot test that fails CI on drift.
- CI now installs runtime dependencies and runs the full `tests/` suite.

### Changed
- Combined read-only auth scopes documented across all install/troubleshooting references.
- README Install section reordered to follow real setup order (Python packages → GCP CLI → ADC auth → plugin install); corrected "Adding a New Domain" guide.

## [1.0.0] - 2026-04-20

### Added
- `cx-rag-researcher` agent: embeds questions, runs semantic vector search across SUMO/Kitsune, Zendesk, and Mozilla Knowledge Base, and synthesizes grounded CX research answers. Supports comparisons across sources, topic discovery, sentiment analysis, and official guidance lookup.
