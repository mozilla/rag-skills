# Installation

## From the marketplace

```bash
/plugin marketplace add https://github.com/mozilla/rag-skills.git
/plugin install rag-skills
```

That's it. Skills load automatically in every Claude Code session.

## Prerequisites (for CX skills)

Skills that query BigQuery need three things:

**1. Python packages.** The skill scripts import these:

```bash
pip install google-auth requests
```

**2. GCP command-line tools.** Set up GCP command line tools, as described on [docs.telemetry.mozilla.org](https://docs.telemetry.mozilla.org/cookbooks/bigquery/access.html#using-the-bq-command-line-tool).

**3. Application Default Credentials.** Authenticate with the read-only BigQuery scope (plus `cloud-platform` for `embed`'s Vertex AI), and set the project to `mozdata`:

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/bigquery.readonly,https://www.googleapis.com/auth/cloud-platform
gcloud config set project mozdata
```

## Updating

To get the latest skills after the repo is updated:

```bash
/plugin update rag-skills
```
