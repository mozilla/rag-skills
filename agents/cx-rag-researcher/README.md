# cx-rag-researcher — Customer Experience RAG Researcher

An agent that researches Mozilla customer experience data across three live sources — SUMO/Kitsune support forums, Zendesk tickets, and the Mozilla Knowledge Base. It uses direct SQL queries for counts and aggregations, semantic vector search for thematic synthesis, and a hybrid of both for grounded, ranked answers about what users are experiencing.

## Prerequisites

Before using this agent you need:

1. **Google Cloud SDK** installed — [install gcloud](https://cloud.google.com/sdk/docs/install)
2. **Authenticated** with application-default credentials:
   ```bash
   gcloud auth application-default login
   ```
3. **GCP project set** to the project name provided by your DE team:
   ```bash
   gcloud config set project <project-provided-by-DE>
   ```

## Installation

Install the rag-skills plugin in Claude Code (one-time setup):

```bash
/plugin marketplace add https://github.com/mozilla/rag-skills.git
/plugin install rag-skills
```

## How to Use

Just ask a question about user experience. The agent picks the right retrieval method automatically — no special commands needed.

The agent will confirm the date range before running, then return a concise answer and offer to go deeper on sources, sentiment, themes, or the queries used.

## What You Can Ask

### Counts & aggregations
Questions about volume, rankings, and statistics — answered with direct SQL across the full dataset.
> "How many Kitsune questions since March 24?"
> "Top 5 topics by ticket volume in April 2026?"
> "Which topic has the lowest average sentiment this quarter?"

### Sentiment & pain points
Questions about what's driving negative feedback — answered with SQL to rank topics by volume, then vector search to explain what users actually wrote.
> "What are the top 3 drivers of negative sentiment about Fenix in March?"
> "What are users most frustrated about with Firefox sync?"

### What users are reporting
Questions about prevalent issues — grounded in volume via SQL, explained via document retrieval.
> "What are users reporting about the password manager in April?"
> "What problems are users filing Zendesk tickets about for Fenix?"

### Comparisons — user experience vs. official guidance
Questions that compare what users are hitting against what Mozilla recommends — hybrid for user data, vector search for KB, gap analysis in synthesis.
> "How does what users report about sync compare to what the KB recommends?"
> "What issues are users hitting that the Knowledge Base doesn't address?"

### Official guidance
Questions about Mozilla's documented solutions.
> "What does Mozilla recommend for Firefox password manager issues?"

### Open-ended exploration
General questions with no implied ranking.
> "Tell me about sync issues on Fenix."
> "Summarize feedback on Firefox for iOS."

## Filters

Scope your question naturally — the agent parses filters silently.

| Filter | How to specify | Example |
|--------|----------------|---------|
| Date range | Say the period | "in Q1 2026", "last month", "since March 24" |
| Single product | Name it | "Firefox for Android", "Fenix", "Firefox desktop" |
| Multiple products | Name both | "Fenix and Firefox desktop" |
| Language / locale | Name the language | "Spanish users", "in French", "en-US" |

**Filter coverage by source:**

| Filter | Kitsune | Zendesk | Knowledge Base |
|--------|---------|---------|----------------|
| Date range | yes | yes | no (no date column) |
| Product | yes | yes | yes |
| Locale | yes | yes | yes |

## Tips

- Always include a time period — the agent will ask if you don't
- Be specific: "Firefox sync bookmarks" beats "Firefox sync"
- For counts or rankings, use signals like "how many", "top N", "most common"
- Ask to see the queries used — the agent can show the SQL and search calls behind any answer
- If results feel thin, ask to broaden the date range or increase the result count

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Authentication rejected (401)` | Re-run `gcloud auth application-default login` |
| `No GCP project configured` | Run `gcloud config set project <project-name-from-DE>` |
| Answer says "no results found" | Broaden the date range, remove product/locale filters, or rephrase |
| Answer feels thin | Ask to broaden the date range or increase the result count |
| Question can't be answered (e.g. "most viewed KB articles") | The required data may not exist in these sources — the agent will tell you and suggest alternatives |
