# Installation

## From the marketplace

```bash
/plugin marketplace add https://github.com/mozilla/rag-skills.git
/plugin install rag-skills
```

That's it. Skills load automatically in every Claude Code session.

## Prerequisites (for CX skills)

Skills that query BigQuery require Google Cloud credentials:

```bash
gcloud auth application-default login
gcloud config set project <project-name-from-DE>
```

## Updating

To get the latest skills after the repo is updated:

```bash
/plugin update rag-skills
```
