import importlib.util
import unittest
from unittest.mock import MagicMock

spec = importlib.util.spec_from_file_location("embed", "skills/embed/scripts/embed.py")
embed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(embed_module)
embed = embed_module.embed


def _mock_session(values):
    """A fake AuthorizedSession whose POST returns the given embedding values."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"predictions": [{"embeddings": {"values": values}}]}
    session = MagicMock()
    session.post.return_value = resp
    return session


class TestEmbed(unittest.TestCase):

    def test_returns_floats(self):
        session = _mock_session([0.1, 0.2, 0.3])
        result = embed("test question", session=session)
        self.assertEqual(result, [0.1, 0.2, 0.3])

    def test_no_null_values(self):
        session = _mock_session([0.1, None, 0.3])
        with self.assertRaises(SystemExit):
            embed("test question", session=session)


if __name__ == "__main__":
    unittest.main()
