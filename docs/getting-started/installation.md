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

**3. Authenticate (service-account impersonation).** Log in with Application Default Credentials and set the project to `mozdata`:

```bash
gcloud auth application-default login
gcloud config set project mozdata
```

The skills connect using a service account: your authenticated credentials are only used to create a new and temporary access token on behalf of the service account defined in each script's `SERVICE_ACCOUNT` constant, which requires the `roles/iam.serviceAccountTokenCreator` role on that service account. Read-only BigQuery (`query`/`vector-search`) and `cloud-platform` (`embed`'s Vertex AI) scopes are enforced on the impersonated token in code, so your login no longer needs `--scopes`.

## Updating

To get the latest skills after the repo is updated:

```bash
/plugin update rag-skills
```
