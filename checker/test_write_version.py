import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import write_version


class WriteVersionTests(unittest.TestCase):
    def test_hash_changes_only_when_feed_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "results.json").write_text(json.dumps([{"id": "a"}]))
            (data / "pib-news.json").write_text("[]")
            write_version.DATA = data
            write_version.main()
            first = json.loads((data / "version.json").read_text())["hash"]
            write_version.main()
            self.assertEqual(first, json.loads((data / "version.json").read_text())["hash"])
            (data / "results.json").write_text(json.dumps([{"id": "a"}, {"id": "b"}]))
            write_version.main()
            self.assertNotEqual(first, json.loads((data / "version.json").read_text())["hash"])


if __name__ == "__main__":
    unittest.main()
