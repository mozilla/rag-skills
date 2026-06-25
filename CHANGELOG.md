# Changelog

## [1.2.0] - 2026-06-25

### Security
- Service-account impersonation: `query`, `vector-search`, and `embed` now reach BigQuery and Vertex AI by impersonating a dedicated read-only service account. The logged-in user's own credentials are used only to create a short-lived token to act as that service account (which requires the `roles/iam.serviceAccountTokenCreator` role on it), enforcing read-only, limited access. Query jobs are billed to a separate compute project, while data is still read only from `mozdata.customer_experience`.

### Changed
- `cx-rag-researcher` agent instructions:
  - Authentication-failure guidance now points to re-running `gcloud auth application-default login` and confirming the token-creator role on the service account.
  - Official-guidance questions ("what does Mozilla recommend") now query the Knowledge Base only.
  - Ranking/count answers report only the aggregated result, never individual thread or document content.
  - No response (including the closing follow-up) may cite figures or content from a source it did not query.
  - An explicitly provided date range is used directly, without asking again.
- Golden-set evaluation now runs fully mocked: no live BigQuery, no command execution, and no permissions granted. Each question is answered over fixture data limited to its expected sources and mode, so correct behavior passes while real regressions are still caught.

### Added
- Fixture data for the mocked golden-set evaluation.

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
