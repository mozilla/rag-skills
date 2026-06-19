#!/usr/bin/env python3
"""
Runs all golden set questions through the cx-rag-researcher agent
and saves responses to tests/golden_set/responses/.

Usage:
    python tests/golden_set/run_agent.py

Prerequisites:
    gcloud auth application-default login
    gcloud config set project <project>
"""

import json
import subprocess
import sys
from pathlib import Path

QUESTIONS_FILE = Path(__file__).parent / "questions.json"
RESPONSES_DIR = Path(__file__).parent / "responses"
PLUGIN_DIR = Path(__file__).parent.parent.parent


def run_question(question: str) -> str:
    prompt = f"Use the rag-skills:cx-rag-researcher agent to answer: {question}"
    result = subprocess.run(
        [
            "claude", "-p",
            "--no-session-persistence",
            # NOTE: permissions are intentionally NOT bypassed. The agent operates on
            # untrusted retrieved content, so running it with bypassPermissions would
            # turn a prompt injection into unrestricted command execution. Configure an
            # explicit allowlist for the skill commands instead if this needs to run
            # non-interactively.
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

    print(f"Running {len(questions)} questions through cx-rag-researcher...\n")

    for q in questions:
        print(f"Q{q['id']}: {q['question']}")
        response = run_question(q["question"])
        response_file = RESPONSES_DIR / f"response_{q['id']}.txt"
        response_file.write_text(response)
        print(f"  Saved to {response_file}\n")

    print(f"Done. Run the evaluator next:")
    print(f"  python tests/golden_set/evaluate.py")


if __name__ == "__main__":
    main()
