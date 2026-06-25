#!/usr/bin/env python3
r"""
Runs a direct read-only SQL query against the Customer Experience tables.

This skill can only ever read any table or view in mozdata.customer_experience;
any reference to another project or dataset is rejected, and only read-only
SELECT queries are accepted. The dataset boundary is enforced authoritatively by
asking BigQuery (via a dry run) which tables a query actually reads, so it cannot
be evaded by SQL syntax the script doesn't parse.

Usage:
    python scripts/query.py --sql "SELECT topic, COUNT(*) AS count
        FROM \`mozdata.customer_experience.kitsune_retrieval_index\`
        WHERE creation_date BETWEEN '2026-03-01' AND '2026-03-31'
        GROUP BY topic ORDER BY count DESC LIMIT 10"

    ({project} may be used as a placeholder for the project — it is replaced with
    the locked project at runtime.)

Prerequisites:
    Python packages: google-auth, requests  ->  pip install google-auth requests
    The Google Cloud account currently authenticated via `gcloud auth application-default
    login` is used only to impersonate the service account defined in SERVICE_ACCOUNT and
    requires the roles/iam.serviceAccountTokenCreator role on that service account. Using
    the service account enforces a read only limited access.

    Authentication is delegated to the google-auth library: it loads and refreshes
    the credentials and attaches them to each request. This script never invokes
    `print-access-token` and never reads, prints, or stores an access token.
"""

import argparse
import re
import sys

# Data boundary: the only project / dataset this skill may ever READ. Any table or
# view inside this dataset is allowed; anything outside it is rejected.
PROJECT = "mozdata"
DATASET = "customer_experience"

# Compute / billing project: query jobs are created and billed here (the service
# account's bigquery.jobUser role lives in this project). Data is still read
# exclusively from PROJECT.DATASET above, cross-project into mozdata.
JOB_PROJECT = "moz-fx-data-proto"

# Least-privilege scope: read-only BigQuery access (no write/DDL at the token level).
SCOPES = ["https://www.googleapis.com/auth/bigquery.readonly"]

# This skill connects to BigQuery using a service account.
# Your own BigQuery credentials are only used to create a new and temporary read-only
# access token on behalf of the service account.
SERVICE_ACCOUNT = "bq-dev-sandbox@moz-fx-data-proto.iam.gserviceaccount.com"

# Cost / size guards. maximumBytesBilled makes BigQuery cancel (and not bill) any
# query that would scan more than this, capping runaway-cost scans. maxResults
# caps how many rows a single response returns, bounding client memory.
MAX_BYTES_BILLED = 50 * 2**30   # 50 GiB
MAX_RESULT_ROWS = 10_000

# Write / DDL / DCL keywords that must never appear anywhere in an accepted query.
# (REPLACE and EXCEPT are intentionally omitted — they are read-only SELECT modifiers.)
_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|"
    r"CALL|LOAD|EXPORT)\b",
    re.IGNORECASE,
)


def _strip_sql(sql: str) -> str:
    """Remove comments and string literals so the guards can't be fooled or tripped
    by keywords/identifiers that appear inside a comment or a quoted value."""
    sql = re.sub(r"--[^\n]*", " ", sql)                      # line comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)    # block comments
    sql = re.sub(r"'(?:[^'\\]|\\.)*'", "''", sql)            # single-quoted strings
    sql = re.sub(r'"(?:[^"\\]|\\.)*"', '""', sql)            # double-quoted strings
    return sql


def assert_select_only(sql: str) -> None:
    """Exit unless `sql` is a single read-only SELECT (optionally WITH ... SELECT).

    Rejects multiple statements and any write/DDL keyword anywhere — including
    inside a CTE, subquery, or EXISTS clause."""
    stripped = _strip_sql(sql).strip()
    if ";" in stripped.rstrip().rstrip(";"):
        print("Only a single statement is allowed (no ';'-separated statements).", file=sys.stderr)
        sys.exit(1)
    if not re.match(r"^\(*\s*(SELECT|WITH)\b", stripped, re.IGNORECASE):
        print("Only read-only SELECT queries are allowed.", file=sys.stderr)
        sys.exit(1)
    if _FORBIDDEN_SQL.search(stripped):
        print("Only read-only SELECT queries are allowed (write/DDL keywords are not permitted).", file=sys.stderr)
        sys.exit(1)


def out_of_scope_tables(referenced: list[dict]) -> list[str]:
    """Given BigQuery's `referencedTables` for a query, return the fully-qualified
    names of any that fall outside the locked dataset. Empty list means in-bounds.

    BigQuery resolves every table/view the query actually reads — through comma
    joins, subqueries, CTEs, wildcards, and views — so this list is authoritative
    where ad-hoc SQL parsing is not."""
    bad = []
    for t in referenced:
        if t.get("projectId") != PROJECT or t.get("datasetId") != DATASET:
            bad.append(f"{t.get('projectId')}.{t.get('datasetId')}.{t.get('tableId')}")
    return bad


def get_auth() -> "object":
    """Return an authorized HTTP session that impersonates a service account.

    Your Application Default Credentials are used only to mint a short-lived,
    read-only access token for the service account defined in SERVICE_ACCOUNT; every
    request is signed with that token, so BigQuery is reached as the service
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


def assert_query_in_scope(sql: str, session) -> None:
    """Ask BigQuery (via a dry run, which neither executes nor bills) which tables
    the query reads, then refuse to run it if any lie outside the locked dataset.

    This is the authoritative dataset boundary: BigQuery, not this script, resolves
    every referenced table, so comma joins, subqueries, CTEs, wildcards, and views
    are all covered."""
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{JOB_PROJECT}/queries"
    resp = _request(session, url, {
        "query": sql,
        "useLegacySql": False,
        "dryRun": True,
        "maximumBytesBilled": str(MAX_BYTES_BILLED),
    })
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


def run_query(sql: str, session) -> list[dict]:
    assert_query_in_scope(sql, session)
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{JOB_PROJECT}/queries"
    resp = _request(session, url, {
        "query": sql,
        "useLegacySql": False,
        "timeoutMs": 30000,
        "maximumBytesBilled": str(MAX_BYTES_BILLED),
        "maxResults": MAX_RESULT_ROWS,
    })
    while not resp.get("jobComplete"):
        job_id = resp["jobReference"]["jobId"]
        resp = _request(
            session,
            f"https://bigquery.googleapis.com/bigquery/v2/projects/{JOB_PROJECT}"
            f"/queries/{job_id}?timeoutMs=30000",
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
    parser = argparse.ArgumentParser(description="Run a read-only SQL query against the CX tables.")
    parser.add_argument("--sql", required=True,
                        help=f"Read-only SELECT over {PROJECT}.{DATASET}.<index>. {{project}} is allowed as a placeholder.")
    args = parser.parse_args()

    sql = args.sql.replace("{project}", PROJECT)
    assert_select_only(sql)

    session = get_auth()
    print("Running query...", file=sys.stderr, flush=True)
    rows = run_query(sql, session)
    print(f"  {len(rows)} rows returned.", file=sys.stderr)
    print(format_results(rows))


if __name__ == "__main__":
    main()
