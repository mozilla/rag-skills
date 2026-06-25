#!/usr/bin/env python3
"""
Returns the gemini-embedding-001 embedding for a given text.

Usage:
    python scripts/embed.py --question "What are users saying about Firefox sync?"

Output:
    JSON array of floats printed to stdout.

Prerequisites:
    Python packages: google-auth, requests  ->  pip install google-auth requests
    The Google Cloud account currently authenticated via `gcloud auth application-default
    login` is used only to impersonate the service account defined in SERVICE_ACCOUNT and
    requires the roles/iam.serviceAccountTokenCreator role on that service account. Using
    the service account enforces limited Vertex AI access.

    Authentication is delegated to the google-auth library: it loads and refreshes
    the credentials and attaches them to each request. This script never invokes
    `print-access-token` and never reads, prints, or stores an access token.
"""

import argparse
import json
import sys

LOCATION = "us-central1"
EMBEDDING_MODEL = "gemini-embedding-001"

# Compute project for Vertex AI: the embedding model runs and bills here (the
# service account's aiplatform.user role lives in this project, and Vertex AI must
# be enabled here). This skill reads no BigQuery data, so there is no data project.
PROJECT = "moz-fx-data-proto"

# Vertex AI is only reachable with the cloud-platform scope (it has no narrower one).
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# This skill connects to Vertex AI using a service account.
# Your own Google Cloud credentials are only used to create a new and temporary
# access token on behalf of the service account.
SERVICE_ACCOUNT = "bq-dev-sandbox@moz-fx-data-proto.iam.gserviceaccount.com"


def get_auth() -> "object":
    """Return an authorized HTTP session that impersonates a service account.

    Your Application Default Credentials are used only to mint a short-lived,
    scoped access token for the service account defined in SERVICE_ACCOUNT; every
    request is signed with that token, so Vertex AI is reached as the service
    account, not as you. No token is ever read, printed, or stored.
    """
    try:
        import google.auth
        from google.auth import impersonated_credentials
        from google.auth.exceptions import DefaultCredentialsError
        from google.auth.transport.requests import AuthorizedSession
    except ImportError:
        print("Missing dependency. Install with: pip install google-auth requests", file=sys.stderr)
        sys.exit(1)

    try:
        source, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    except DefaultCredentialsError:
        print("GCP authentication required. Run: gcloud auth application-default login", file=sys.stderr)
        sys.exit(1)

    credentials = impersonated_credentials.Credentials(
        source_credentials=source,
        target_principal=SERVICE_ACCOUNT,
        target_scopes=SCOPES,
    )
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
