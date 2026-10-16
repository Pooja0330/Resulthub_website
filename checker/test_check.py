import unittest

from check import classify, host_allowed, is_stale_notice, normalize_notice_url


class CheckerSafetyTests(unittest.TestCase):
    def test_notice_url_keeps_content_identifiers(self):
        first = normalize_notice_url("https://www.example.gov.in/notice?id=123&utm_source=mail")
        second = normalize_notice_url("https://example.gov.in/notice?id=456")
        self.assertNotEqual(first, second)

    def test_notice_url_removes_tracking_only(self):
        first = normalize_notice_url("https://www.example.gov.in/notice?id=123&utm_source=mail")
        second = normalize_notice_url("https://example.gov.in/notice?id=123")
        self.assertEqual(first, second)

    def test_allowlist_requires_exact_host_or_subdomain(self):
        self.assertTrue(host_allowed("https://results.example.gov.in/", ["example.gov.in"]))
        self.assertFalse(host_allowed("https://example.gov.in.attacker.test/", ["example.gov.in"]))
        self.assertFalse(host_allowed("http://example.gov.in/", ["example.gov.in"]))

    def test_classifies_exam_result(self):
        self.assertEqual(classify("SSC CGL Tier I Result 2026"), "result")

    def test_ignores_unrelated_cultural_event(self):
        self.assertIsNone(classify("Annual Cultural Festival 2026"))

    def test_keeps_exam_results_in_official_press_releases(self):
        self.assertEqual(classify("Press Release: CBSE Declares Class X Result 2026"), "result")

    def test_old_explicit_feed_date_is_stale(self):
        self.assertTrue(is_stale_notice("Recruitment Result", "Mon, 01 Jan 2024 00:00:00 GMT"))

    def test_current_feed_date_is_not_stale(self):
        self.assertFalse(is_stale_notice("Recruitment Result", "Fri, 16 Oct 2026 09:00:00 GMT"))


if __name__ == "__main__":
    unittest.main()
