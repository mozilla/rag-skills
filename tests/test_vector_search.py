import importlib.util
import unittest
from unittest.mock import patch

import sys
spec = importlib.util.spec_from_file_location("vector_search", "skills/vector-search/scripts/vector_search.py")
vs_module = importlib.util.module_from_spec(spec)
sys.modules["vector_search"] = vs_module
spec.loader.exec_module(vs_module)
search = vs_module.search
format_results = vs_module.format_results


class TestVectorSearchEmptyResults(unittest.TestCase):

    @patch("vector_search._bq_query", return_value=[])
    def test_empty_dataset_returns_empty_list(self, _):
        result = search(
            table="proj.dataset.table",
            embedding_column="embedding",
            columns=None,
            embedding=[0.1, 0.2, 0.3],
            token="tok",
            project="proj",
            top_k=5,
            date_column=None,
            date_from=None,
            date_to=None,
            filters=[],
        )
        self.assertEqual(result, [])

    def test_format_empty_results_does_not_crash(self):
        output = format_results([], label="test")
        self.assertIn("No results", output)


if __name__ == "__main__":
    unittest.main()
