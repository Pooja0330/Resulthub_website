import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo_pages import render_detail, safe_https

class BuildSeoPagesTests(unittest.TestCase):
    def test_detail_page_has_unique_canonical_and_structured_data(self):
        item = {
            "id": "abc123456789",
            "title": "SSC CGL <Result> 2026",
            "category": "result",
            "source_name": "Staff Selection Commission",
            "url": "https://ssc.gov.in/results",
            "detected_at": "2026-10-30T17:15:00+00:00",
        }
        page = render_detail(item)
        self.assertIn("https://goresulthub.com/updates/abc123456789.html", page)
        self.assertIn('type="application/ld+json"', page)
        self.assertIn("SSC CGL &lt;Result&gt; 2026", page)
        self.assertIn('href="https://ssc.gov.in/results"', page)

    def test_detail_rejects_invalid_id(self):
        self.assertEqual(render_detail({"id": "../bad", "title": "Bad"}), "")

    def test_only_https_official_links_are_rendered(self):
        self.assertEqual(safe_https("http://example.com"), "")
        self.assertEqual(safe_https("https://example.com/path"), "https://example.com/path")

if __name__ == "__main__":
    unittest.main()
