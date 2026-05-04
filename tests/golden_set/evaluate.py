,#!/usr/bin/env python3
"""
LLM-as-judge evaluator for cx-rag-researcher agent responses.

Sends each saved response to Claude for evaluation against correctness
criteria. Writes a report.json with pass/fail per question.

Usage:
    python tests/golden_set/evaluate.py

Prerequisites:
    Run run_agent.py first to generate response files.
"""

import json
import subprocess
import sys
from pathlib import Path

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESPONSES_DIR = Path(__file__).parent / "responses"
REPORT_FILE = Path(__file__).parent / "report.json"

JUDGE_PROMPT = """You are evaluating a response from the cx-rag-researcher agent — a Mozilla CX research assistant.

Question: {question}
Expected sources: {expected_sources}
Expected retrieval mode: {expected_mode}

Agent response:
---
{response}
---

Evaluate against these criteria. Each is PASS or FAIL:

1. CORRECT_SOURCES: Did the agent use the right sources?
   - User sentiment/feedback → Kitsune and/or Zendesk (not KB alone)
   - Official guidance ("what does Mozilla recommend") → Knowledge Base only
   - Comparison or mixed → all three sources
   Expected: {expected_sources}

2. CORRECT_MODE: Did the agent use the right retrieval mode?
   - Counting/ranking questions → SQL (response should contain numbers/counts)
   - Official guidance → vector search only
   - User experience questions → hybrid (SQL for ranking + vector for content)
   Expected: {expected_mode}

3. NO_ZENDESK_SENTIMENT: If the response discusses user sentiment or feelings, does it avoid drawing those conclusions from Zendesk? Only Kitsune should be used for sentiment.

4. NO_FABRICATION: Is the response grounded in retrieved data? It must not invent statistics or claim data it could not have retrieved.

5. FOLLOW_UP: Does the response end with an invitation to refine or dig deeper?

Respond only in this JSON format:
{{
  "CORRECT_SOURCES": {{"result": "PASS or FAIL", "reason": "one sentence"}},
  "CORRECT_MODE": {{"result": "PASS or FAIL", "reason": "one sentence"}},
  "NO_ZENDESK_SENTIMENT": {{"result": "PASS or FAIL", "reason": "one sentence"}},
  "NO_FABRICATION": {{"result": "PASS or FAIL", "reason": "one sentence"}},
  "FOLLOW_UP": {{"result": "PASS or FAIL", "reason": "one sentence"}}
}}"""


def judge_response(question: dict, response: str) -> dict:
    prompt = JUDGE_PROMPT.format(
        question=question["question"],
        expected_sources=", ".join(question["expected_sources"]),
        expected_mode=question["expected_mode"],
        response=response,
    )
    result = subprocess.run(
        ["claude", "-p", "--no-session-persistence", prompt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Judge error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    output = result.stdout.strip()
    start = output.find("{")
    end = output.rfind("}") + 1
    return json.loads(output[start:end])


def main():
    questions = json.loads(QUESTIONS_FILE.read_text())
    report = []
    total_passed = 0
    total_failed = 0

    print("Evaluating responses...\n")

    for q in questions:
        response_file = RESPONSES_DIR / f"response_{q['id']}.txt"
        if not response_file.exists():
            print(f"[SKIP] Q{q['id']}: response file not found — run run_agent.py first")
            continue

        response = response_file.read_text()
        print(f"Judging Q{q['id']}: {q['question'][:60]}...")
        evaluation = judge_response(q, response)

        failures = [k for k, v in evaluation.items() if v["result"] == "FAIL"]
        passed = len(evaluation) - len(failures)
        total_passed += passed
        total_failed += len(failures)

        status = "PASS" if not failures else "FAIL"
        print(f"  [{status}] {passed}/{len(evaluation)} checks passed")
        for k in failures:
            print(f"    - {k}: {evaluation[k]['reason']}")

        report.append({
            "id": q["id"],
            "question": q["question"],
            "status": status,
            "evaluation": evaluation,
        })

    REPORT_FILE.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to {REPORT_FILE}")
    print(f"{total_passed} passed, {total_failed} failed.")

    if total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
