#!/usr/bin/env python3
"""Refresh the committed BigQuery schema snapshot for the CX retrieval-index tables.

Run this whenever the upstream tables change; commit the updated snapshot.json
alongside any documentation edits:

    python tests/schema/refresh_snapshot.py

It queries `INFORMATION_SCHEMA.COLUMNS` (via the `query` skill's auth/transport)
and writes column name -> data type for each table. `tests/test_schema.py` then
asserts the live schema still matches this snapshot, failing CI on drift.

Requires GCP application-default credentials:
    gcloud auth application-default login
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(__file__).parent / "snapshot.json"
DATASET = "mozdata.customer_experience"
TABLES = [
    "kitsune_retrieval_index",
    "zendesk_retrieval_index",
    "knowledge_base_retrieval_index",
]

_spec = importlib.util.spec_from_file_location("query", ROOT / "skills/query/scripts/query.py")
query = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(query)


def fetch_schema() -> dict:
    session = query.get_auth()
    table_list = ", ".join(f"'{t}'" for t in TABLES)
    sql = f"""SELECT table_name, column_name, data_type
FROM `{DATASET}.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name IN ({table_list})
ORDER BY table_name, ordinal_position"""
    rows = query.run_query(sql, session)
    schema: dict[str, dict[str, str]] = {t: {} for t in TABLES}
    for r in rows:
        schema[r["table_name"]][r["column_name"]] = r["data_type"]
    return schema


def main() -> None:
    schema = fetch_schema()
    SNAPSHOT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    total = sum(len(cols) for cols in schema.values())
    print(f"Wrote {SNAPSHOT} — {total} columns across {len(schema)} tables.")


if __name__ == "__main__":
    main()
