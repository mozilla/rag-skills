---
name: embed
description: Receives a text question and returns its embedding vector using gemini-embedding-001 via Vertex AI. Use this when you need a semantic embedding for a question — for downstream vector search, similarity comparison, or passing to another tool.
---

# Embed Skill

Embeds a text question using `gemini-embedding-001` (Vertex AI, project `mozdata`) and returns the resulting vector as a JSON array.

## Usage

```bash
python "${CLAUDE_PLUGIN_ROOT:?set by the plugin system; if empty, invoke this via the Skill tool}"/skills/embed/scripts/embed.py --question "<your question>"
```
``
Output is a JSON array of 3072 floats printed to stdout:

```json
[0.012, -0.034, 0.091, ...]
```

## Steps

1. Run the script with the user's question as `--question`.
2. Capture stdout — that is the embedding vector.
3. Return or pass the vector as needed (e.g. to the `vector-search` skill).

## Authentication

This skill connects to Vertex AI using a service account — the `cloud-platform` scope is enforced on the impersonated token in code. Just log in:

```bash
gcloud auth application-default login
```

Your authenticated Google Cloud credentials are only used to create a new and temporary access token on behalf of the service account defined in `SERVICE_ACCOUNT`, which requires the `roles/iam.serviceAccountTokenCreator` role on that service account. Your login no longer needs `--scopes`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `GCP authentication required` / `API error 401` | Re-run `gcloud auth application-default login`; confirm you have `roles/iam.serviceAccountTokenCreator` on the service account in `SERVICE_ACCOUNT` |
| `Missing dependency` | `pip install google-auth requests` |
| `Unexpected response from Vertex AI` | Confirm Vertex AI is enabled in project `mozdata` and the embedding model is available |
