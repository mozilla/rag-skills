"""Schema-drift and naming-convention tests for the CX retrieval-index tables.

Offline (run in CI, no credentials):
  - LLM-derived columns use the correct per-source prefix
    (kitsune=question_, zendesk=ticket_, KB=article_)
  - each source exposes the expected set of LLM concepts
  - docs reference only real columns and no stale/unprefixed names

Live (skipped without GCP application-default credentials):
  - the committed snapshot still matches BigQuery; fails on drift.
    Refresh with: python tests/schema/refresh_snapshot.py
"""

import importlib.util
import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_FILE = ROOT / "tests/schema/snapshot.json"

# LLM-derived columns are prefixed by source.
PREFIX = {
    "kitsune_retrieval_index": "question_",
    "zendesk_retrieval_index": "ticket_",
    "knowledge_base_retrieval_index": "article_",
}

# LLM "concept" stems each source is expected to expose (prefix stripped).
# KB is authored content: no language or sentiment columns.
EXPECTED_LLM_CONCEPTS = {
    "kitsune_retrieval_index": {
        "summary_llm", "category_llm", "language_llm",
        "topics_llm", "entities_llm", "sentiment_score",
    },
    "zendesk_retrieval_index": {
        "summary_llm", "category_llm", "language_llm",
        "topics_llm", "entities_llm", "sentiment_score",
    },
    "knowledge_base_retrieval_index": {
        "summary_llm", "category_llm", "topics_llm", "entities_llm",
    },
}

# Documentation that must stay consistent with the schema.
DOC_FILES = [
    ROOT / "agents/cx-rag-researcher.md",
    ROOT / "skills/query/SKILL.md",
    ROOT / "agents/cx-rag-researcher/references/kitsune_schema.md",
    ROOT / "agents/cx-rag-researcher/references/zendesk_schema.md",
    ROOT / "agents/cx-rag-researcher/references/knowledge_base_schema.md",
    ROOT / "agents/cx-rag-researcher/references/sumo_kitsune_overview.md",
    ROOT / "agents/cx-rag-researcher/references/zendesk_overview.md",
    ROOT / "agents/cx-rag-researcher/references/knowledge_base_overview.md",
]

# Names that must never appear in the docs (regressions we have already fixed).
# Word boundaries ensure source-prefixed names (e.g. question_category_llm) do
# NOT match the bare forms below.
FORBIDDEN = [
    r"_generated\b",                 # old LLM-column suffix; now _llm
    r"customer_experience_derived",  # old dataset name; now customer_experience
    r"\bcategory_llm\b",             # must be <source>_category_llm
    r"\bsummary_llm\b",
    r"\btopics_llm\b",
    r"\bentities_llm\b",
    r"\blanguage_llm\b",
    r"\bsentiment_score\b",          # must be question_/ticket_-prefixed
    r"DATE\(creation_date\)",        # creation_date is a DATE on every table
    r"\{project\}",                  # tables are fully qualified to mozdata
]

# Source-prefixed LLM column names cited in docs, mapped to their table.
PREFIX_TO_TABLE = {p: t for t, p in PREFIX.items()}
CITED_LLM_RE = re.compile(r"\b(question|ticket|article)_[a-z0-9_]*?(?:_llm|_sentiment_score)\b")

APPLICATION_CREDENTIALS_FILE = Path(os.path.expanduser("~/.config/gcloud/application_default_credentials.json"))


def _application_credentials_available() -> bool:
    # The live query path impersonates a service account using the default or locally
    # authenticated credentials; without them, skip rather than fail.
    return APPLICATION_CREDENTIALS_FILE.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))


def _load_snapshot() -> dict:
    return json.loads(SNAPSHOT_FILE.read_text())


def _fetch_live() -> dict:
    spec = importlib.util.spec_from_file_location(
        "refresh_snapshot", ROOT / "tests/schema/refresh_snapshot.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.fetch_schema()


class TestSchemaConventions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = _load_snapshot()

    def test_llm_columns_use_source_prefix(self):
        for table, cols in self.snapshot.items():
            prefix = PREFIX[table]
            for col in cols:
                if col.endswith("_llm") or col.endswith("_sentiment_score"):
                    self.assertTrue(
                        col.startswith(prefix),
                        f"{table}.{col} should start with '{prefix}'",
                    )

    def test_expected_llm_concepts_present(self):
        for table, expected in EXPECTED_LLM_CONCEPTS.items():
            prefix = PREFIX[table]
            present = {
                col[len(prefix):]
                for col in self.snapshot[table]
                if col.startswith(prefix)
                and (col.endswith("_llm") or col.endswith("_sentiment_score"))
            }
            self.assertEqual(
                present, expected,
                f"{table} LLM concepts differ from expectation",
            )

    def test_docs_have_no_stale_or_unprefixed_names(self):
        for doc in DOC_FILES:
            text = doc.read_text()
            for pattern in FORBIDDEN:
                self.assertIsNone(
                    re.search(pattern, text),
                    f"{doc.name} contains forbidden pattern /{pattern}/",
                )

    def test_docs_cite_only_real_llm_columns(self):
        for doc in DOC_FILES:
            for match in CITED_LLM_RE.finditer(doc.read_text()):
                name = match.group(0)
                table = PREFIX_TO_TABLE[name.split("_", 1)[0] + "_"]
                self.assertIn(
                    name, self.snapshot[table],
                    f"{doc.name} cites {name}, which is not a column of {table}",
                )

    @unittest.skipUnless(_application_credentials_available(), "no GCP application-default credentials")
    def test_live_schema_matches_snapshot(self):
        try:
            live = _fetch_live()
        except SystemExit:
            self.skipTest("could not query BigQuery (auth/network)")
        self.assertEqual(
            live, self.snapshot,
            "Live BigQuery schema differs from snapshot. "
            "Refresh with: python tests/schema/refresh_snapshot.py "
            "(and update the schema reference docs to match).",
        )


if __name__ == "__main__":
    unittest.main()
