---
name: embed
description: Receives a text question and returns its embedding vector using gemini-embedding-001 via Vertex AI. Use this when you need a semantic embedding for a question — for downstream vector search, similarity comparison, or passing to another tool.
---

# Embed Skill

Embeds a text question using `gemini-embedding-001` and returns the resulting vector as a JSON array.

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/embed/scripts/embed.py --question "<your question>"
```

Output is a JSON array of 3072 floats printed to stdout:

```json
[0.012, -0.034, 0.091, ...]
```

## Steps

1. Run the script with the user's question as `--question`.
2. Capture stdout — that is the embedding vector.
3. Return or pass the vector as needed.

## Prerequisites

Google Cloud SDK with active credentials:

```bash
gcloud auth application-default login
gcloud config set project <project-id>
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `GCP authentication required` | Run `gcloud auth application-default login` |
| `No GCP project configured` | Run `gcloud config set project <project-id>` |
| `API error 401` | Re-authenticate with `gcloud auth application-default login` |
