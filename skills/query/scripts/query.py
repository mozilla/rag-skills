#!/usr/bin/env python3
"""
Runs a direct SQL query against BigQuery and prints results as a formatted table.

Reference tables by their full name, e.g. mozdata.customer_experience.kitsune_retrieval_index.

Usage:
    python scripts/query.py --sql "SELECT topic, COUNT(*) AS count
        FROM \`mozdata.customer_experience.kitsune_retrieval_index\`
        WHERE creation_date BETWEEN '2026-03-01' AND '2026-03-31'
        GROUP BY topic ORDER BY count DESC LIMIT 10"

Prerequisites:
    Google Cloud SDK (gcloud CLI) with application-default credentials.
    gcloud auth application-default login
    gcloud config set project <project-id>
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request


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


def _request(url: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("Authentication rejected (401). Run: gcloud auth application-default login", file=sys.stderr)
            sys.exit(1)
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message", f"HTTP {e.code}")
        except Exception:
            msg = f"HTTP {e.code}"
        print(f"API error: {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def run_query(sql: str, token: str, project: str) -> list[dict]:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries"
    resp = _request(url, token, {"query": sql, "useLegacySql": False, "timeoutMs": 30000})
    while not resp.get("jobComplete"):
        job_id = resp["jobReference"]["jobId"]
        resp = _request(
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}"
            f"/queries/{job_id}?timeoutMs=30000",
            token,
        )
    fields = resp.get("schema", {}).get("fields", [])
    rows = resp.get("rows", [])
    col_names = [f["name"] for f in fields]
    return [dict(zip(col_names, (cell.get("v") for cell in row["f"]))) for row in rows]


def format_results(rows: list[dict]) -> str:
    if not rows:
        return "No results."
    headers = list(rows[0].keys())
    col_widths = {
        h: max(len(h), max((len(str(r.get(h) or "")) for r in rows), default=0))
        for h in headers
    }
    sep = "  ".join("-" * col_widths[h] for h in headers)
    lines = [
        "  ".join(h.ljust(col_widths[h]) for h in headers),
        sep,
    ]
    for row in rows:
        lines.append("  ".join(str(row.get(h) or "").ljust(col_widths[h]) for h in headers))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a direct SQL query against BigQuery.")
    parser.add_argument("--sql", required=True,
                        help="SQL query to run. Reference tables by full name, e.g. mozdata.customer_experience.<table>.")
    args = parser.parse_args()

    token, project = get_auth()
    sql = args.sql

    print("Running query...", file=sys.stderr, flush=True)
    rows = run_query(sql, token, project)
    print(f"  {len(rows)} rows returned.", file=sys.stderr)
    print(format_results(rows))


if __name__ == "__main__":
    main()
