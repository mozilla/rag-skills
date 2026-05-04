#!/usr/bin/env python3
"""
Returns the gemini-embedding-001 embedding for a given text.

Usage:
    python scripts/embed.py --question "What are users saying about Firefox sync?"

Output:
    JSON array of floats printed to stdout.

Prerequisites:
    Google Cloud SDK (gcloud CLI) with application-default credentials.
    gcloud auth application-default login
    gcloud config set project <project-id-provided-by-Data-Engineering>
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

LOCATION = "us-central1"
EMBEDDING_MODEL = "gemini-embedding-001"


def get_auth() -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True, text=True, check=True,
        )
        token = result.stdout.strip()
    except subprocess.CalledProcessError:
        print("GCP authentication required. Run: gcloud auth application-default login", file=sys.stderr)
        sys.exit(1)

    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, check=True,
        )
        project = result.stdout.strip()
        if not project or project == "(unset)":
            print("No GCP project configured. Run: gcloud config set project <project-id>", file=sys.stderr)
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("Could not read GCP project.", file=sys.stderr)
        sys.exit(1)

    return token, project


def embed(question: str, token: str, project: str) -> list[float]:
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{LOCATION}/publishers/google/models/{EMBEDDING_MODEL}:predict"
    )
    payload = json.dumps({
        "instances": [{"content": question, "task_type": "RETRIEVAL_QUERY"}]
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return data["predictions"][0]["embeddings"]["values"]
    except urllib.error.HTTPError as e:
        print(f"API error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, IndexError):
        print("Unexpected response from Vertex AI embedding API.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed a question using gemini-embedding-001.")
    parser.add_argument("--question", required=True, help="Text to embed.")
    args = parser.parse_args()

    token, project = get_auth()
    vector = embed(args.question, token, project)
    print(json.dumps(vector))


if __name__ == "__main__":
    main()
