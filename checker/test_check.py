import unittest

from check import classify, exam_year_from_title, extract_notice_date, host_allowed, infer_exam_category, is_stale_notice, normalize_notice_url


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

    def test_old_uploaded_date_in_notice_title_is_stale(self):
        self.assertTrue(is_stale_notice("Result uploaded on 13/02/2024", ""))

    def test_banking_sources_use_banking_filter_family(self):
        self.assertEqual(infer_exam_category("IBPS PO result", "Institute of Banking Personnel Selection", "ibps"), "Banking")

    def test_railway_sources_use_railways_filter_family(self):
        self.assertEqual(infer_exam_category("NTPC result", "Railway Recruitment Board", "rrb-bilaspur"), "Railways")

    def test_source_id_preserves_teaching_family_for_kvs(self):
        self.assertEqual(infer_exam_category("Recruitment notification", "Kendriya Vidyalaya Sangathan", "kvs"), "Teaching / Eligibility")

    def test_extracts_explicit_official_upload_date(self):
        self.assertEqual(extract_notice_date("Notice ABC Date of Upload: 01/10/2026 Download PDF"), "01 Oct 2026")

    def test_does_not_guess_date_when_listing_has_no_labelled_date(self):
        self.assertEqual(extract_notice_date("SSC CGL 2026 Apply Online"), "")

    def test_exam_year_is_only_returned_when_explicit(self):
        self.assertEqual(exam_year_from_title("SSC CGL Tier-I Result 2026"), "2026")
        self.assertEqual(exam_year_from_title("Recruitment Result"), "")

    def test_generic_call_letters_landing_page_is_not_a_notice(self):
        self.assertIsNone(classify("Call Letters"))

    def test_classifies_public_exam_notice(self):
        self.assertEqual(classify("Public Notice: Revised Examination Schedule 2026"), "exam_schedule")

    def test_classifies_admission_notice(self):
        self.assertEqual(classify("Admission Notice for Entrance Examination 2026"), "notification")

    def test_pib_feed_indexes_general_press_releases(self):
        from check import classify_source_title
        source = {"include_all_items": True}
        self.assertEqual(
            classify_source_title("Government announces a new public initiative", source),
            "notification",
        )

    def test_generic_navigation_is_not_indexed_as_pib_notice(self):
        from check import classify_source_title
        self.assertIsNone(
            classify_source_title("Read More", {"include_all_items": True})
        )

    def test_pib_navigation_links_are_not_indexed_as_updates(self):
        from check import classify_source_title
        for title in (
            "Skip to Content",
            "AccessibilityStatement",
            "Screen Reader Access",
            "About Us",
            "Main Functions",
            "Press Information Bureau",
        ):
            with self.subTest(title=title):
                self.assertIsNone(
                    classify_source_title(title, {"include_all_items": True})
                )


if __name__ == "__main__":
    unittest.main()
