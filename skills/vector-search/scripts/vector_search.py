#!/usr/bin/env python3
"""
Runs VECTOR_SEARCH against any BigQuery table with an embedding column.

Usage:
    python scripts/vector_search.py \
        --embedding-file /tmp/embedding.json \
        --table project.dataset.table_name \
        [--embedding-column embedding] \
        [--columns col1,col2,...] \
        [--label "Display Name"] \
        [--date-column COLUMN] \
        [--s YYYY-MM-DD] [--e YYYY-MM-DD] \
        [--filter column:value] \
        [--top-k 5]

Prerequisites:
    Google Cloud SDK (gcloud CLI) with application-default credentials.
    gcloud auth application-default login
    gcloud config set project <project-id>
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

DEFAULT_TOP_K = 5
DEFAULT_EMBEDDING_COLUMN = "embedding"


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


def _bq_query(sql: str, token: str, project: str) -> list[dict]:
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


def _sanitize(value: str) -> str:
    return re.sub(r"['\";\\]", "", value)


def search(
    table: str,
    embedding_column: str,
    columns: list[str] | None,
    embedding: list[float],
    token: str,
    project: str,
    top_k: int,
    date_column: str | None,
    date_from: str | None,
    date_to: str | None,
    filters: list[tuple[str, str]],
) -> list[dict]:
    literal = "[" + ",".join(str(v) for v in embedding) + "]"
    col_expr = ", ".join(f"base.{c}" for c in columns) if columns else "base.*"

    conds = []
    if date_column and date_from:
        conds.append(f"DATE(base.{_sanitize(date_column)}) >= '{_sanitize(date_from)}'")
    if date_column and date_to:
        conds.append(f"DATE(base.{_sanitize(date_column)}) <= '{_sanitize(date_to)}'")
    for col, val in filters:
        conds.append(f"LOWER(base.{_sanitize(col)}) LIKE LOWER('%{_sanitize(val)}%')")

    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    sql = f"""
    SELECT {col_expr}, distance
    FROM VECTOR_SEARCH(
        TABLE `{table}`, '{embedding_column}',
        (SELECT {literal} AS {embedding_column}),
        top_k => {top_k}, distance_type => 'COSINE'
    )
    {where}
    ORDER BY distance ASC
    """
    return _bq_query(sql, token, project)


def format_results(rows: list[dict], label: str) -> str:
    if not rows:
        return f"=== {label} ===\nNo results found.\n"
    parts = [f"=== {label} ({len(rows)} results) ==="]
    for i, row in enumerate(rows, 1):
        lines = [f"{k}: {v}" for k, v in row.items() if v is not None]
        if lines:
            parts.append(f"[{i}]\n" + "\n".join(lines))
    return "\n".join(parts)


def resolve_table(table_ref: str, project: str) -> str:
    if table_ref.count(".") == 1:
        return f"{project}.{table_ref}"
    return table_ref


def main() -> None:
    parser = argparse.ArgumentParser(description="Vector search against any BigQuery embedding table.")
    parser.add_argument("--embedding-file", required=True,
                        help="Path to JSON file containing the embedding vector.")
    parser.add_argument("--table", required=True,
                        help="BigQuery table: 'dataset.table' or 'project.dataset.table'.")
    parser.add_argument("--embedding-column", default=DEFAULT_EMBEDDING_COLUMN,
                        help=f"Name of the embedding column (default: {DEFAULT_EMBEDDING_COLUMN}).")
    parser.add_argument("--columns",
                        help="Comma-separated list of columns to return (default: all).")
    parser.add_argument("--label",
                        help="Display name for the results header (default: table name).")
    parser.add_argument("--date-column",
                        help="Column name to apply date range filters against.")
    parser.add_argument("--s", metavar="YYYY-MM-DD",
                        help="Filter records on or after this date (requires --date-column).")
    parser.add_argument("--e", metavar="YYYY-MM-DD",
                        help="Filter records on or before this date (requires --date-column).")
    parser.add_argument("--filter", action="append", default=[], metavar="column:value",
                        help="Partial-match filter as 'column:value'. Repeatable.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help=f"Number of results to return (default: {DEFAULT_TOP_K}).")
    args = parser.parse_args()

    try:
        with open(args.embedding_file) as f:
            embedding = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Failed to read embedding file: {e}", file=sys.stderr)
        sys.exit(1)

    columns = [c.strip() for c in args.columns.split(",")] if args.columns else None

    parsed_filters = []
    for filt in args.filter:
        if ":" not in filt:
            print(f"Invalid --filter format '{filt}': expected 'column:value'", file=sys.stderr)
            sys.exit(1)
        col, _, val = filt.partition(":")
        parsed_filters.append((col.strip(), val.strip()))

    token, project = get_auth()
    table_id = resolve_table(args.table, project)
    label = args.label or args.table.split(".")[-1]

    print(f"Searching {label}...", file=sys.stderr, flush=True)
    rows = search(
        table_id, args.embedding_column, columns, embedding, token, project,
        args.top_k, args.date_column, args.s, args.e, parsed_filters,
    )
    print(f"  Retrieved {len(rows)} results.", file=sys.stderr)
    print(format_results(rows, label))


if __name__ == "__main__":
    main()
