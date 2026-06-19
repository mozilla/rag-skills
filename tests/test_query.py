import importlib.util
import unittest

spec = importlib.util.spec_from_file_location("query", "skills/query/scripts/query.py")
query_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query_module)
format_results = query_module.format_results
assert_select_only = query_module.assert_select_only
out_of_scope_tables = query_module.out_of_scope_tables

KITSUNE = "`mozdata.customer_experience.kitsune_retrieval_index`"


def _ref(project, dataset, table):
    return {"projectId": project, "datasetId": dataset, "tableId": table}


class TestFormatResults(unittest.TestCase):

    def test_empty_results_are_explicit(self):
        self.assertIn("No results", format_results([]))

    def test_rows_render_as_table(self):
        out = format_results([{"topic": "passwords", "count": 74}])
        self.assertIn("topic", out)
        self.assertIn("passwords", out)
        self.assertIn("74", out)


class TestSelectOnly(unittest.TestCase):

    def test_plain_select_ok(self):
        assert_select_only(f"SELECT a FROM {KITSUNE}")

    def test_with_cte_ok(self):
        assert_select_only(f"WITH c AS (SELECT 1 AS x) SELECT x FROM c")

    def test_keyword_inside_string_literal_ok(self):
        # 'update' inside a quoted value must not trip the guard.
        assert_select_only(f"SELECT title FROM {KITSUNE} WHERE title LIKE '%update%'")

    def test_insert_rejected(self):
        with self.assertRaises(SystemExit):
            assert_select_only("INSERT INTO t VALUES (1)")

    def test_write_keyword_anywhere_rejected(self):
        with self.assertRaises(SystemExit):
            assert_select_only(f"SELECT * FROM {KITSUNE} UNION ALL DELETE FROM u")

    def test_multiple_statements_rejected(self):
        with self.assertRaises(SystemExit):
            assert_select_only(f"SELECT 1 FROM {KITSUNE}; DROP TABLE t")


class TestOutOfScopeTables(unittest.TestCase):
    """out_of_scope_tables receives BigQuery's authoritative list of every table a
    query reads, so it catches references that ad-hoc SQL parsing would miss."""

    def test_any_table_in_dataset_is_in_scope(self):
        refs = [_ref("mozdata", "customer_experience", "kitsune_retrieval_index"),
                _ref("mozdata", "customer_experience", "some_other_table_or_view")]
        self.assertEqual(out_of_scope_tables(refs), [])

    def test_other_dataset_flagged(self):
        refs = [_ref("mozdata", "other_dataset", "secrets")]
        self.assertEqual(out_of_scope_tables(refs), ["mozdata.other_dataset.secrets"])

    def test_other_project_flagged(self):
        refs = [_ref("evil", "customer_experience", "kitsune_retrieval_index")]
        self.assertEqual(out_of_scope_tables(refs),
                         ["evil.customer_experience.kitsune_retrieval_index"])

    def test_comma_join_smuggled_table_flagged(self):
        # The old regex guard missed the second table in `FROM a, b`; BigQuery
        # reports both, so the smuggled out-of-dataset table is now caught.
        refs = [_ref("mozdata", "customer_experience", "kitsune_retrieval_index"),
                _ref("secret-project", "private", "exfil")]
        self.assertEqual(out_of_scope_tables(refs), ["secret-project.private.exfil"])

    def test_empty_reference_list_is_in_scope(self):
        self.assertEqual(out_of_scope_tables([]), [])


if __name__ == "__main__":
    unittest.main()
