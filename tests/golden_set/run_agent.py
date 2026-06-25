#!/usr/bin/env python3
"""
Runs the golden set fully mocked — NO live BigQuery, NO tool execution, and NO
permissions granted in advance.

Each question is answered by the cx-rag-researcher agent reasoning over injected
fixture data (tests/golden_set/fixtures/) with all execution tools disabled, so
nothing real runs and no command ever needs approval.

The fixtures injected for a question are scoped to that question's
`expected_sources` and `expected_mode`:
  - SQL / ranking mode  -> only the aggregated `sql_ranking` rows
  - vector mode         -> only the `documents` snippets
  - hybrid mode         -> both
Scoping the data to what a correct answer would actually have retrieved is what
keeps the test honest: correct behaviour passes, while a regression (dropping the
follow-up, drawing sentiment from Zendesk, inventing data not present, etc.) is
caught by the judge. It does NOT inject other sources, so the agent is never
handed data it could only have by misrouting.

Usage:
    python tests/golden_set/run_agent.py
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
QUESTIONS_FILE = HERE / "questions.json"
RESPONSES_DIR = HERE / "responses"
FIXTURES_DIR = HERE / "fixtures"
PLUGIN_DIR = HERE.parent.parent

# Execution tools the agent must never use in the mocked run. Disabling them
# guarantees no command runs and no permission is ever requested — the agent can
# only reason over the fixtures injected into the prompt.
DISALLOWED_TOOLS = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch"

# Maps an `expected_sources` label to its fixture file stem and display label.
SOURCE_FILES = {
    "Kitsune": ("kitsune", "KITSUNE (SUMO support forums — user posts; the source for sentiment)"),
    "Zendesk": ("zendesk", "ZENDESK (support tickets — what users report; NOT for sentiment)"),
    "Knowledge Base": ("knowledge_base", "KNOWLEDGE BASE (official Mozilla articles; no sentiment)"),
}


def fixtures_for(question: dict) -> str:
    """Build the data block for a question, scoped to its sources and mode."""
    mode = question.get("expected_mode", "hybrid")
    include_ranking = mode in ("sql", "hybrid")
    include_docs = mode in ("vector", "hybrid")

    blocks = []
    for source in question["expected_sources"]:
        key, label = SOURCE_FILES[source]
        data = json.loads((FIXTURES_DIR / f"{key}.json").read_text())
        scoped = {}
        if include_ranking and "sql_ranking" in data:
            scoped["sql_ranking"] = data["sql_ranking"]
        if include_docs and "documents" in data:
            scoped["documents"] = data["documents"]
        if scoped:
            blocks.append(f"[{label}]\n{json.dumps(scoped, indent=2, ensure_ascii=False)}")
    return "\n\n".join(blocks)


def build_prompt(question: str, fixtures: str) -> str:
    return (
        "Use the rag-skills:cx-rag-researcher agent to answer the question below.\n\n"
        "TEST MODE — read carefully:\n"
        "- All data retrieval has ALREADY been performed. The DATA blocks below are the\n"
        "  exact results the skills returned. Do NOT run, retry, or call any tool or\n"
        "  command; there is nothing to authenticate or query.\n"
        "- Ground every claim strictly in the data shown. Use the SQL ranking for\n"
        "  counts/rankings and the document snippets for content. Do not introduce any\n"
        "  figure or detail that is not present below.\n"
        "- End with your usual invitation to refine or dig deeper.\n\n"
        f"Question: {question}\n\n"
        "=== RETRIEVED DATA (mocked fixtures) ===\n"
        f"{fixtures}\n"
    )


def run_question(question: dict) -> str:
    prompt = build_prompt(question["question"], fixtures_for(question))
    result = subprocess.run(
        [
            "claude", "-p",
            "--no-session-persistence",
            "--disallowedTools", DISALLOWED_TOOLS,
            "--plugin-dir", str(PLUGIN_DIR),
            prompt,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def main():
    RESPONSES_DIR.mkdir(exist_ok=True)
    questions = json.loads(QUESTIONS_FILE.read_text())

    print(f"Running {len(questions)} questions (mocked — no tools, no permissions)...\n")

    for q in questions:
        print(f"Q{q['id']}: {q['question']}")
        response = run_question(q)
        response_file = RESPONSES_DIR / f"response_{q['id']}.txt"
        response_file.write_text(response)
        print(f"  Saved to {response_file}\n")

    print("Done. Run the evaluator next:")
    print("  python tests/golden_set/evaluate.py")


if __name__ == "__main__":
    main()
