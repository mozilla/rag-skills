import importlib.util
import json
import sys
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("embed", "skills/embed/scripts/embed.py")
embed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(embed_module)
embed = embed_module.embed


def _mock_response(values):
    body = json.dumps({"predictions": [{"embeddings": {"values": values}}]}).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestEmbed(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_returns_floats(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([0.1, 0.2, 0.3])
        result = embed("test question", token="tok", project="proj")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("urllib.request.urlopen")
    def test_no_null_values(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response([0.1, None, 0.3])
        with self.assertRaises(SystemExit):
            embed("test question", token="tok", project="proj")


if __name__ == "__main__":
    unittest.main()
