import importlib.util
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("vector_search", "skills/vector-search/scripts/vector_search.py")
vs_module = importlib.util.module_from_spec(spec)
sys.modules["vector_search"] = vs_module
spec.loader.exec_module(vs_module)
search = vs_module.search
format_results = vs_module.format_results

KITSUNE = "mozdata.customer_experience.kitsune_retrieval_index"


def _search(**overrides):
    args = dict(
        table=KITSUNE,
        embedding_column="embedding",
        columns=None,
        embedding=[0.1, 0.2, 0.3],
        session=None,
        top_k=5,
        date_column=None,
        date_from=None,
        date_to=None,
        filters=[],
    )
    args.update(overrides)
    return search(**args)


class TestVectorSearch(unittest.TestCase):

    @patch("vector_search._bq_query", return_value=[])
    def test_empty_dataset_returns_empty_list(self, _):
        self.assertEqual(_search(), [])

    @patch("vector_search._bq_query", return_value=[])
    def test_values_are_parameterized_not_interpolated(self, mock_q):
        _search(
            columns=["title", "content", "question_sentiment_score"],
            date_column="creation_date",
            date_from="2026-01-01",
            filters=[("product", "Fenix")],
        )
        sql, _session, params = mock_q.call_args.args
        # Values go in as bound parameters, never written into the SQL text.
        self.assertIn("@query_embedding", sql)
        self.assertIn("@date_from", sql)
        self.assertNotIn("Fenix", sql)
        self.assertNotIn("0.1", sql)
        names = {p["name"] for p in params}
        self.assertEqual(names, {"query_embedding", "date_from", "filter_0"})

    def test_wrong_project_rejected(self):
        with self.assertRaises(SystemExit):
            _search(table="other_project.customer_experience.kitsune_retrieval_index")

    def test_wrong_dataset_rejected(self):
        with self.assertRaises(SystemExit):
            _search(table="mozdata.other_dataset.kitsune_retrieval_index")

    @patch("vector_search._bq_query", return_value=[])
    def test_any_table_in_dataset_is_allowed(self, _):
        # Any table or view in the locked dataset is permitted; the dataset boundary
        # is enforced at query time by the dry run, not by a fixed table list.
        self.assertEqual(_search(table="mozdata.customer_experience.some_view"), [])

    def test_injection_in_output_column_rejected(self):
        with self.assertRaises(SystemExit):
            _search(columns=["title", "x) FROM `evil.p.t` -- "])

    def test_injection_in_filter_column_rejected(self):
        with self.assertRaises(SystemExit):
            _search(filters=[("product); DROP TABLE x; --", "Fenix")])

    @patch("vector_search._bq_query", return_value=[])
    def test_bare_table_name_is_resolved(self, _):
        # A bare table name resolves to the locked project.dataset.
        self.assertEqual(_search(table="kitsune_retrieval_index"), [])

    def test_format_empty_results_does_not_crash(self):
        self.assertIn("No results", format_results([], label="test"))


if __name__ == "__main__":
    unittest.main()
