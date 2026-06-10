import importlib.util
import unittest

spec = importlib.util.spec_from_file_location("query", "skills/query/scripts/query.py")
query_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query_module)
format_results = query_module.format_results


class TestFormatResults(unittest.TestCase):

    def test_empty_results_are_explicit(self):
        # An empty result set must produce an unmistakable "no data" string
        # so the agent can halt-and-report instead of inventing an answer.
        out = format_results([])
        self.assertIn("No results", out)

    def test_rows_render_as_table(self):
        rows = [{"topic": "passwords", "count": 74}]
        out = format_results(rows)
        self.assertIn("topic", out)
        self.assertIn("passwords", out)
        self.assertIn("74", out)


if __name__ == "__main__":
    unittest.main()
