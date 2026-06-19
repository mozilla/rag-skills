#!/usr/bin/env python3
"""
Runs VECTOR_SEARCH against the Customer Experience retrieval indexes.

This skill can only ever read tables and views in mozdata.customer_experience;
any other project or dataset is rejected. The dataset boundary is enforced
authoritatively by asking BigQuery (via a dry run) which tables the query reads.

Usage:
    python scripts/vector_search.py \
        --embedding-file /tmp/embedding.json \
        --table mozdata.customer_experience.<index> \
        [--embedding-column embedding] \
        [--columns col1,col2,...] \
        [--label "Display Name"] \
        [--date-column COLUMN] \
        [--s YYYY-MM-DD] [--e YYYY-MM-DD] \
        [--filter column:value] \
        [--top-k 5]

Safety:
    - The query embedding, dates, and filter values are passed to BigQuery as typed
      query parameters (never interpolated into the SQL text).
    - Project/dataset/table/column names are SQL identifiers (which cannot be
      parameters). The dataset is locked to mozdata.customer_experience, table and
      column names must be plain identifiers (no SQL metacharacters), and a dry
      run confirms BigQuery reads nothing outside the dataset. Columns that do not
      exist are rejected by BigQuery itself.

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
import re
import sys

DEFAULT_TOP_K = 5
DEFAULT_EMBEDDING_COLUMN = "embedding"

# Least-privilege scope: read-only BigQuery access (no write/DDL at the token level).
SCOPES = ["https://www.googleapis.com/auth/bigquery.readonly"]

# maximumBytesBilled makes BigQuery cancel (and not bill) any query that would
# scan more than this, capping runaway-cost scans. (Row count is already bounded
# by top_k.)
MAX_BYTES_BILLED = 50 * 2**30   # 50 GiB

# The only project / dataset this skill may ever touch.
PROJECT = "mozdata"
DATASET = "customer_experience"

# Table and column names are SQL identifiers and cannot be bound as parameters, so
# they are written into the SQL text. To make that safe, every identifier must match
# this pattern — a plain name with no dots, quotes, spaces, or other metacharacters —
# so nothing can break out of the identifier position. Whether a column actually
# exists is left to BigQuery (the query fails cleanly if it does not).
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def resolve_table(table_ref: str) -> str:
    """Validate `table_ref` is a table or view in the locked project/dataset and
    return the canonical `mozdata.customer_experience.<name>`. Exit on anything else.

    Any table or view in the dataset is allowed; the project and dataset are locked,
    and the name must be a plain identifier. The dry run later confirms the resolved
    query reads nothing outside the dataset."""
    parts = table_ref.strip("`").split(".")
    name = parts[-1]
    if len(parts) >= 2 and parts[-2] != DATASET:
        print(f"Dataset not allowed: only {DATASET} is permitted.", file=sys.stderr)
        sys.exit(1)
    if len(parts) == 3 and parts[0] != PROJECT:
        print(f"Project not allowed: only {PROJECT} is permitted.", file=sys.stderr)
        sys.exit(1)
    if len(parts) > 3 or not _IDENTIFIER_RE.match(name):
        print(
            f"Table not allowed: {table_ref}. This skill may only read a table or "
            f"view in {PROJECT}.{DATASET}.",
            file=sys.stderr,
        )
        sys.exit(1)
    return f"{PROJECT}.{DATASET}.{name}"


def _check_identifier(col: str, kind: str) -> None:
    """Reject anything that is not a plain SQL identifier, so a column/table name
    cannot break out of its position in the SQL text."""
    if not _IDENTIFIER_RE.match(col):
        print(f"Invalid {kind} '{col}': must be a plain column name.", file=sys.stderr)
        sys.exit(1)


def _scalar_param(name: str, type_: str, value: str) -> dict:
    return {
        "name": name,
        "parameterType": {"type": type_},
        "parameterValue": {"value": value},
    }


def _request(session, url: str, payload: dict | None = None) -> dict:
    try:
        resp = session.post(url, json=payload, timeout=60) if payload is not None \
            else session.get(url, timeout=60)
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
    return resp.json()


def out_of_scope_tables(referenced: list[dict]) -> list[str]:
    """Given BigQuery's `referencedTables` for a query, return the fully-qualified
    names of any that fall outside the locked dataset. Empty list means in-bounds."""
    bad = []
    for t in referenced:
        if t.get("projectId") != PROJECT or t.get("datasetId") != DATASET:
            bad.append(f"{t.get('projectId')}.{t.get('datasetId')}.{t.get('tableId')}")
    return bad


def assert_query_in_scope(sql: str, session, params: list | None = None) -> None:
    """Ask BigQuery (via a dry run, which neither executes nor bills) which tables
    the query reads, then refuse to run it if any lie outside the locked dataset."""
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries"
    body = {"query": sql, "useLegacySql": False, "dryRun": True,
            "maximumBytesBilled": str(MAX_BYTES_BILLED)}
    if params:
        body["parameterMode"] = "NAMED"
        body["queryParameters"] = params
    resp = _request(session, url, body)
    referenced = resp.get("statistics", {}).get("query", {}).get("referencedTables", [])
    if not referenced:
        print(
            "Refusing to run: failed to identify which tables this query reads, so "
            "the dataset boundary cannot be verified. The query is not run.",
            file=sys.stderr,
        )
        sys.exit(1)
    bad = out_of_scope_tables(referenced)
    if bad:
        print(
            f"Refusing to run: query reads {', '.join(bad)}, outside the allowed "
            f"dataset. This skill may only read tables and views in {PROJECT}.{DATASET}.",
            file=sys.stderr,
        )
        sys.exit(1)


def _bq_query(sql: str, session, params: list | None = None) -> list[dict]:
    assert_query_in_scope(sql, session, params)
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries"
    body = {"query": sql, "useLegacySql": False, "timeoutMs": 30000,
            "maximumBytesBilled": str(MAX_BYTES_BILLED)}
    if params:
        body["parameterMode"] = "NAMED"
        body["queryParameters"] = params
    resp = _request(session, url, body)
    while not resp.get("jobComplete"):
        job_id = resp["jobReference"]["jobId"]
        resp = _request(
            session,
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}"
            f"/queries/{job_id}?timeoutMs=30000",
        )
    fields = resp.get("schema", {}).get("fields", [])
    rows = resp.get("rows", [])
    col_names = [f["name"] for f in fields]
    return [dict(zip(col_names, (cell.get("v") for cell in row["f"]))) for row in rows]


def search(
    table: str,
    embedding_column: str,
    columns: list[str] | None,
    embedding: list[float],
    session,
    top_k: int,
    date_column: str | None,
    date_from: str | None,
    date_to: str | None,
    filters: list[tuple[str, str]],
) -> list[dict]:
    # Lock the table to the dataset and require every identifier to be a plain name
    # (so it cannot break out of the SQL); the dry run in _bq_query then confirms the
    # resolved query reads nothing outside the dataset.
    table = resolve_table(table)
    _check_identifier(embedding_column, "embedding column")
    if columns:
        for c in columns:
            _check_identifier(c, "column")
    if date_column:
        _check_identifier(date_column, "date column")
    for col, _ in filters:
        _check_identifier(col, "filter column")

    # Validate values that will be bound as parameters.
    try:
        embedding = [float(v) for v in embedding]
    except (TypeError, ValueError):
        print("Embedding must be a list of numbers.", file=sys.stderr)
        sys.exit(1)
    for d in (date_from, date_to):
        if d is not None and not _DATE_RE.match(d):
            print(f"Invalid date '{d}': expected YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)

    col_expr = ", ".join(f"base.{c}" for c in columns) if columns else "base.*"

    # Values are passed as typed query parameters, never interpolated into the SQL.
    params = [{
        "name": "query_embedding",
        "parameterType": {"type": "ARRAY", "arrayType": {"type": "FLOAT64"}},
        "parameterValue": {"arrayValues": [{"value": repr(v)} for v in embedding]},
    }]

    conds = []
    if date_column and date_from:
        conds.append(f"DATE(base.{date_column}) >= @date_from")
        params.append(_scalar_param("date_from", "DATE", date_from))
    if date_column and date_to:
        conds.append(f"DATE(base.{date_column}) <= @date_to")
        params.append(_scalar_param("date_to", "DATE", date_to))
    for i, (col, val) in enumerate(filters):
        pname = f"filter_{i}"
        conds.append(f"LOWER(base.{col}) LIKE LOWER(@{pname})")
        params.append(_scalar_param(pname, "STRING", f"%{val}%"))

    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    sql = f"""
    SELECT {col_expr}, distance
    FROM VECTOR_SEARCH(
        TABLE `{table}`, '{embedding_column}',
        (SELECT @query_embedding AS {embedding_column}),
        top_k => {int(top_k)}, distance_type => 'COSINE'
    )
    {where}
    ORDER BY distance ASC
    """
    return _bq_query(sql, session, params)


def format_results(rows: list[dict], label: str) -> str:
    if not rows:
        return f"=== {label} ===\nNo results found.\n"
    parts = [f"=== {label} ({len(rows)} results) ==="]
    for i, row in enumerate(rows, 1):
        lines = [f"{k}: {v}" for k, v in row.items() if v is not None]
        if lines:
            parts.append(f"[{i}]\n" + "\n".join(lines))
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vector search against a Customer Experience index.")
    parser.add_argument("--embedding-file", required=True,
                        help="Path to JSON file containing the embedding vector.")
    parser.add_argument("--table", required=True,
                        help=f"A table or view in {PROJECT}.{DATASET} (e.g. {PROJECT}.{DATASET}.kitsune_retrieval_index).")
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

    label = args.label or args.table.split(".")[-1]

    session = get_auth()
    print(f"Searching {label}...", file=sys.stderr, flush=True)
    rows = search(
        args.table, args.embedding_column, columns, embedding, session,
        args.top_k, args.date_column, args.s, args.e, parsed_filters,
    )
    print(f"  Retrieved {len(rows)} results.", file=sys.stderr)
    print(format_results(rows, label))


if __name__ == "__main__":
    main()
