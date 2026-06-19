#!/usr/bin/env python3
"""
Returns the gemini-embedding-001 embedding for a given text.

Usage:
    python scripts/embed.py --question "What are users saying about Firefox sync?"

Output:
    JSON array of floats printed to stdout.

Prerequisites:
    Python packages: google-auth, requests  ->  pip install google-auth requests
    Application Default Credentials, set up once with:
        gcloud auth application-default login

    Authentication is delegated to the google-auth library: it loads and refreshes
    the credentials and attaches them to each request. This script never invokes
    `print-access-token` and never reads, prints, or stores an access token.
"""

import argparse
import json
import sys

LOCATION = "us-central1"
EMBEDDING_MODEL = "gemini-embedding-001"

# The only project this skill may ever use (Vertex AI must be enabled here).
PROJECT = "mozdata"

# Vertex AI is only reachable with the cloud-platform scope (it has no narrower one).
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_auth() -> "object":
    """Return an authorized HTTP session.

    Authentication uses Application Default Credentials via google-auth: the
    returned session signs each request internally. This never invokes
    `print-access-token` and never reads, prints, or stores an access token.
    Authenticate once with: gcloud auth application-default login
    """
    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError
        from google.auth.transport.requests import AuthorizedSession
    except ImportError:
        print("Missing dependency. Install with: pip install google-auth requests", file=sys.stderr)
        sys.exit(1)

    try:
        credentials, _ = google.auth.default(scopes=SCOPES)
    except DefaultCredentialsError:
        print("GCP authentication required. Run: gcloud auth application-default login", file=sys.stderr)
        sys.exit(1)

    return AuthorizedSession(credentials)


def embed(question: str, session) -> list[float]:
    url = (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{LOCATION}/publishers/google/models/{EMBEDDING_MODEL}:predict"
    )
    payload = {"instances": [{"content": question, "task_type": "RETRIEVAL_QUERY"}]}
    try:
        resp = session.post(url, json=payload, timeout=60)
    except Exception as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code == 401:
        print("Authentication rejected (401). Run: gcloud auth application-default login", file=sys.stderr)
        sys.exit(1)
    if resp.status_code >= 400:
        try:
            msg = resp.json().get("error", {}).get("message", f"HTTP {resp.status_code}")
        except Exception:
            msg = f"HTTP {resp.status_code}"
        print(f"API error: {msg}", file=sys.stderr)
        sys.exit(1)

    try:
        values = resp.json()["predictions"][0]["embeddings"]["values"]
    except (KeyError, IndexError, ValueError):
        print("Unexpected response from Vertex AI embedding API.", file=sys.stderr)
        sys.exit(1)

    if not values or any(v is None for v in values):
        print("Embedding API returned null or empty values.", file=sys.stderr)
        sys.exit(1)
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed a question using gemini-embedding-001.")
    parser.add_argument("--question", required=True, help="Text to embed.")
    args = parser.parse_args()

    session = get_auth()
    vector = embed(args.question, session)
    print(json.dumps(vector))


if __name__ == "__main__":
    main()
