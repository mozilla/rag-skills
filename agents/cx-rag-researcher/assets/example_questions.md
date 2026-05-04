# Example Questions

Sample questions this agent handles well, grouped by the retrieval mode each triggers.

---

## Counts & Aggregations *(SQL only)*

- "How many Kitsune questions have we had since March 24, 2026?"
- "What are the top 5 topics by number of questions in April 2026?"
- "How many Zendesk tickets were filed about Fenix last month?"
- "What is the ticket count broken down by product for Q1 2026?"
- "Which topic has the lowest average sentiment score on Kitsune this quarter?"
- "What percentage of Kitsune questions are about customization?"
- "How many KB articles exist per category?"
- "How has ticket volume trended week by week in March 2026?"

---

## Sentiment & Pain Points *(Hybrid — SQL ranks, vector search explains)*

- "What were the top 3 drivers of negative sentiment about Fenix in March 2026?"
- "What are the main pain points for Firefox on Android this quarter?"
- "What are users most frustrated about with Firefox sync?"
- "Which topics are generating the most negative sentiment on Kitsune?"
- "What are the top complaints from Spanish-speaking users about Firefox desktop?"
- "What issues drove the most negative feedback about Firefox for iOS in April?"

---

## What Users Are Saying *(Hybrid — SQL grounds, vector search synthesizes)*

- "What are users reporting about the Firefox password manager in April 2026?"
- "What are users experiencing with Firefox sync after the latest update?"
- "What problems are users filing Zendesk tickets about for Fenix?"
- "What are the most common issues users raise about tab management?"
- "What are users saying about Firefox memory usage?"

---

## Comparisons — User Experience vs. Official Guidance *(Hybrid + KB vector search)*

- "How does what Firefox users report about the password manager compare to what Mozilla recommends?"
- "What are users experiencing with sync, and how does it align with KB guidance?"
- "Do Kitsune threads and Zendesk tickets point to the same problems for Firefox on Android?"
- "What sync issues are users hitting that the Knowledge Base doesn't address?"

---

## Official Guidance *(Vector search on KB only)*

- "What does Mozilla recommend for Firefox password manager issues?"
- "What KB articles exist for Firefox sync troubleshooting?"
- "What is the official guidance for users who can't access websites in Firefox?"

---

## Open-Ended Exploration *(Vector search only)*

- "Tell me about sync issues on Fenix."
- "Give me an overview of mobile user complaints."
- "Summarize feedback on Firefox for iOS."
- "What are the main themes in SUMO for the Search & Navigation category?"

---

## Tips for Better Results

- Always include a time period — the agent will ask if you don't
- Be specific about the feature ("Firefox sync bookmarks" vs. "Firefox sync")
- For counts or rankings, include signals like "how many", "top N", "most common"
- If results feel thin, ask to broaden the date range or increase the result count
- You can scope by product ("Fenix", "Firefox desktop") or language ("Spanish users", "en-US")
- After any answer, ask to see the queries used to understand how the data was retrieved
