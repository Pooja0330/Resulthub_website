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


class SeoQualityTests(unittest.TestCase):
    def test_boilerplate_description_is_replaced_and_article_schema_used(self):
        from build_seo_pages import render_detail
        item = {"id": "abc123456789", "title": "SSC CGL Result 2026", "category": "result",
                "source_name": "Staff Selection Commission", "url": "https://ssc.gov.in/results",
                "description": "Potential update detected on an allowlisted official website.",
                "detected_at": "2026-11-20T10:00:00+00:00"}
        page = render_detail(item)
        self.assertNotIn("Potential update detected", page)
        self.assertIn('"@type":"NewsArticle"', page)
        self.assertIn("BreadcrumbList", page)

    def test_old_boilerplate_pages_are_noindex_but_fresh_ones_indexed(self):
        from build_seo_pages import is_indexable
        old = {"id": "a" * 12, "description": "Potential update detected", "detected_at": "2020-01-01T00:00:00+00:00"}
        fresh = {"id": "b" * 12, "description": "Potential update detected",
                 "detected_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
        self.assertFalse(is_indexable(old))
        self.assertTrue(is_indexable(fresh))

    def test_hub_page_lists_items_with_item_list_schema(self):
        from build_seo_pages import render_hub, HUBS
        page = render_hub(HUBS[0], [{"id": "abc123456789", "title": "Sample Result 2026", "source_name": "Board"}])
        self.assertIn("ItemList", page)
        self.assertIn("updates/abc123456789.html", page)


class LiveListQualityTests(unittest.TestCase):
    def test_nav_junk_scholarships_and_duplicates_are_excluded(self):
        from build_seo_pages import is_live_item, dedupe_by_title
        junk = {"id": "j" * 12, "category": "notification",
                "title": "Accreditations Mandatory Disclosure NBA ISO Certificate Student Activities Syllabus Time Table Prospectus"}
        scholarship = {"id": "s" * 12, "category": "scholarship", "title": "Merit Scholarship 2026 Notification"}
        good = {"id": "g" * 12, "category": "result", "title": "SSC CGL Final Result 2026"}
        self.assertFalse(is_live_item(junk))
        self.assertFalse(is_live_item(scholarship))
        self.assertTrue(is_live_item(good))
        self.assertEqual(len(dedupe_by_title([good, dict(good, id="h" * 12)])), 1)
