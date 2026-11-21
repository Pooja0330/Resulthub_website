import unittest

from check import classify, deduplicate_published_results, discover_listing_urls, exam_year_from_title, extract_notice_date, get_with_retries, host_allowed, infer_exam_category, is_exam_alert_source, is_speculative_status_title, is_stale_notice, normalize_notice_title, normalize_notice_url
from bs4 import BeautifulSoup


class CheckerSafetyTests(unittest.TestCase):
    def test_listing_discovery_prefers_official_notice_pages(self):
        html = """
        <a href="/latest-updates/">Latest Updates</a>
        <a href="https://attacker.example/latest-results/">Latest Results</a>
        <a href="/downloads/notice.pdf">Recruitment Notice PDF</a>
        <a href="/contact/">Contact Us</a>
        <a href="/results/">Results</a>
        """
        soup = BeautifulSoup(html, "html.parser")
        found = discover_listing_urls(
            soup,
            "https://example.gov.in/",
            ["example.gov.in"],
        )
        self.assertIn("https://example.gov.in/latest-updates/", found)
        self.assertIn("https://example.gov.in/results/", found)
        self.assertFalse(any("attacker.example" in url for url in found))
        self.assertFalse(any(url.endswith(".pdf") for url in found))
        self.assertFalse(any("/contact" in url for url in found))

    def test_listing_discovery_includes_bounded_pagination(self):
        html = """
        <a href="/notices/">Latest Notices</a>
        <a href="/notices/?page=2">Next Page</a>
        <a href="/notices/?page=3">Page 3</a>
        <a href="/notices/?page=4">Page 4</a>
        <a href="https://outside.example/page/2">Next Page</a>
        """
        found = discover_listing_urls(
            BeautifulSoup(html, "html.parser"),
            "https://example.gov.in/",
            ["example.gov.in"],
            limit=6,
        )
        self.assertIn("https://example.gov.in/notices/?page=2", found)
        self.assertFalse(any("outside.example" in url for url in found))
        self.assertLessEqual(len(found), 6)

    def test_listing_discovery_is_bounded(self):
        html = "".join(
            f'<a href="/notices/page-{n}/">Latest Notices {n}</a>'
            for n in range(10)
        )
        found = discover_listing_urls(
            BeautifulSoup(html, "html.parser"),
            "https://example.gov.in/",
            ["example.gov.in"],
            limit=2,
        )
        self.assertEqual(len(found), 2)

    def test_source_registry_coalesces_same_official_url_and_preserves_coverage(self):
        from check import coalesce_sources_by_url
        sources = [
            {"id": "jee-main", "name": "JEE Main", "url": "https://jeemain.nta.nic.in/",
             "kind": "html", "categories": ["result", "notification"],
             "exam_category": "Entrance & Eligibility", "allowed_hosts": ["nta.nic.in"]},
            {"id": "jee-main-notices", "name": "JEE Main public notices", "url": "https://www.jeemain.nta.nic.in/?utm_source=feed",
             "kind": "html", "categories": ["admit_card", "answer_key", "exam_schedule"],
             "exam_category": "JEE Main", "allowed_hosts": ["jeemain.nta.nic.in"],
             "discover_listing_pages": True},
            {"id": "neet", "name": "NEET UG", "url": "https://neet.nta.nic.in/",
             "kind": "html", "categories": ["result"], "exam_category": "NEET UG",
             "allowed_hosts": ["nta.nic.in"]},
        ]
        merged = coalesce_sources_by_url(sources)
        self.assertEqual(len(merged), 2)
        jee = next(item for item in merged if item["id"] == "jee-main")
        self.assertEqual(set(jee["categories"]), {"result", "notification", "admit_card", "answer_key", "exam_schedule"})
        self.assertIn("jee-main-notices", jee["source_alias_ids"])
        self.assertIn("JEE Main", jee["exam_categories"])
        self.assertTrue(jee["discover_listing_pages"])
        self.assertEqual(merged[1]["id"], "neet")

    def test_source_registry_keeps_default_notice_limit_when_no_override_is_set(self):
        from check import coalesce_sources_by_url
        merged = coalesce_sources_by_url([
            {"id": "one", "url": "https://example.gov.in/", "kind": "html"},
            {"id": "two", "url": "https://www.example.gov.in/?utm_source=feed", "kind": "html"},
        ])
        self.assertEqual(len(merged), 1)
        self.assertNotIn("max_new", merged[0])

    def test_discovery_index_without_official_link_creates_unverified_report_only(self):
        from unittest.mock import patch
        from check import fetch_source
        class FakeResponse:
            url = "https://www.resultbharat.com/latestjobs_more.html"
            text = '<a href="/example-notice.html">SSC CGL Recruitment Notification 2026</a>'
            content = text.encode("utf-8")
            headers = {"content-type": "text/html"}
        source = {
            "id": "resultbharat-jobs",
            "name": "ResultBharat Latest Jobs index",
            "url": "https://www.resultbharat.com/latestjobs_more.html",
            "allowed_hosts": ["resultbharat.com", "www.resultbharat.com"],
            "discovery_only": True,
            "official_hosts": ["ssc.gov.in"],
            "authority_sources": [{
                "id": "ssc", "name": "Staff Selection Commission",
                "allowed_hosts": ["ssc.gov.in"],
            }],
            "max_new": 5,
        }
        with patch("check.get_with_retries", return_value=FakeResponse()):
            found = fetch_source(source)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["reported_only"])
        self.assertTrue(found[0]["reference_only"])
        self.assertEqual(found[0]["source_id"], "resultbharat-jobs")
        self.assertIn("resultbharat.com", found[0]["url"])

    def test_official_registry_covers_added_admissions_and_scholarship_sources(self):
        import json
        from pathlib import Path
        registry_path = Path(__file__).resolve().parents[1] / "checker" / "sources.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        by_id = {source["id"]: source for source in registry["sources"]}
        expected = {
            "ailet-nlu-delhi": "nationallawuniversitydelhi.in",
            "josaa-counselling": "josaa.admissions.nic.in",
            "nic-admissions-counselling": "admissions.nic.in",
            "icar-nta-exams": "exams.nta.nic.in",
            "national-scholarship-portal": "scholarships.gov.in",
        }
        for source_id, host in expected.items():
            with self.subTest(source_id=source_id):
                self.assertIn(source_id, by_id)
                self.assertTrue(by_id[source_id]["enabled"])
                self.assertIn(host, by_id[source_id]["allowed_hosts"])

    def test_reported_only_result_is_explicitly_unverified(self):
        from check import build_result
        item = {
            "id": "reported-123",
            "title": "Example Recruitment Notification 2026",
            "category": "notification",
            "source_name": "ResultBharat — Latest Jobs",
            "source_id": "resultbharat-jobs",
            "url": "https://www.resultbharat.com/example-notice.html",
            "source_url": "https://www.resultbharat.com/example-notice.html",
            "reference_only": True,
            "reported_only": True,
            "reported_by": "ResultBharat",
        }
        result = build_result(item, "2026-11-21T00:00:00+00:00")
        self.assertTrue(result["reported_only"])
        self.assertTrue(result["reference_only"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["verification_status"], "reported_unverified")
        self.assertEqual(result["reported_by"], "ResultBharat")

    def test_source_registry_does_not_merge_different_notice_pages(self):
        from check import coalesce_sources_by_url
        sources = [
            {"id": "sbi-careers", "name": "SBI Careers", "url": "https://sbi.bank.in/careers/"},
            {"id": "sbi-results", "name": "SBI Results", "url": "https://sbi.bank.in/careers/results"},
        ]
        self.assertEqual([x["id"] for x in coalesce_sources_by_url(sources)], ["sbi-careers", "sbi-results"])

    def test_published_results_deduplicate_identical_official_urls(self):
        from check import deduplicate_published_results

        records = [
            {"id": "first", "title": "Railway result notice", "url": "https://www.rrc-wr.com/"},
            {"id": "duplicate", "title": "Another title for same page", "url": "https://rrc-wr.com/?utm_source=telegram"},
            {"id": "distinct", "title": "Detailed result notice", "url": "https://rrc-wr.com/Results.aspx?id=123"},
        ]
        cleaned = deduplicate_published_results(records)
        self.assertEqual([item["id"] for item in cleaned], ["first", "distinct"])


    def test_jkinfo_discovery_source_is_restricted_to_official_destination_hosts(self):
        authority_sources = [
            {"id": "ibps", "name": "IBPS", "allowed_hosts": ["ibps.in", "ibpsreg.ibps.in"]}
        ]
        self.assertTrue(host_allowed("https://ibpsreg.ibps.in/rrbxvaug26/login.php", authority_sources[0]["allowed_hosts"]))
        self.assertFalse(host_allowed("https://jkinfo.in/page.php?b=IBPS", authority_sources[0]["allowed_hosts"]))
        self.assertFalse(host_allowed("https://ibpsreg.ibps.in.attacker.example/login", authority_sources[0]["allowed_hosts"]))

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

    def test_pib_all_release_sources_are_excluded_from_exam_alerts(self):
        self.assertFalse(is_exam_alert_source({
            "id": "pib-press-releases",
            "name": "Press Information Bureau (PIB) — Press Releases",
            "enabled": True,
            "include_all_items": True,
        }))
        self.assertFalse(is_exam_alert_source({
            "id": "pib-custom-feed",
            "name": "Custom source",
            "enabled": True,
        }))

    def test_regular_exam_source_remains_enabled(self):
        self.assertTrue(is_exam_alert_source({
            "id": "ssc",
            "name": "Staff Selection Commission",
            "enabled": True,
        }))

    def test_classifies_exam_result(self):
        self.assertEqual(classify("SSC CGL Tier I Result 2026"), "result")

    def test_classifies_ssc_identity_and_document_verification_notices(self):
        self.assertEqual(
            classify("Identity Verification (IV) for candidates shortlisted in FRTA of Combined Hindi Translators Examination, 2025"),
            "merit_list",
        )
        self.assertEqual(
            classify("Document Verification Schedule for shortlisted candidates"),
            "merit_list",
        )

    def test_classifies_ssc_city_intimation_and_admission_certificate_notice(self):
        self.assertEqual(
            classify("Information regarding the city of examination and admission certificate for candidates of Sub-Inspector Examination, 2026"),
            "admit_card",
        )

    def test_classifies_ibps_pre_examination_training_update(self):
        self.assertEqual(
            classify("Online Pre-Examination Training for Candidates under CRP-RRBs-XV"),
            "exam_schedule",
        )

    def test_keeps_long_detailed_official_exam_notice_title(self):
        from check import is_navigation_noise_title
        title = (
            "NOTICE: Candidates shortlisted for the written examination are informed that "
            "document verification and medical examination will be conducted according to "
            "the revised schedule published by the Commission for the recruitment process "
            "and all eligible applicants must bring the required original certificates."
        )
        self.assertFalse(is_navigation_noise_title(title))

    def test_rejects_gseb_concatenated_registration_navigation_cluster(self):
        from check import is_navigation_noise_title
        title = (
            "Board Website School Registration Teacher Registration SSC Exam Registration "
            "February - March 2027 HSC General Exam Registration February - March 2027 "
            "HSC Science Exam Registration February - March 2027 GSOS HSC GENERAL EXAM "
            "HALL TICKET NOV-DEC-2026 GSOS SSC E"
        )
        self.assertTrue(is_navigation_noise_title(title))

    def test_keeps_long_single_exam_notice(self):
        from check import is_navigation_noise_title
        self.assertFalse(is_navigation_noise_title(
            "Gujarat Board publishes the revised 2027 Higher Secondary examination "
            "timetable with subject-wise dates and candidate instructions."
        ))

    def test_rejects_bpsc_generic_navigation_cluster(self):
        from check import is_navigation_noise_title
        self.assertTrue(is_navigation_noise_title(
            "All Notices Programs Interviews Results Advertisement"
        ))
        self.assertTrue(is_navigation_noise_title(
            "Advertisements Online Application View Marksheet Interview Letters"
        ))

    def test_rejects_repeated_gujarat_board_exam_registration_cluster(self):
        from check import is_navigation_noise_title
        title = (
            "Board Website School Registration Teacher Registration SSC Exam Registration "
            "February - March 2027 HSC General Exam Registration February - March 2027 "
            "HSC Science Exam Registration February - March 2027 GSOS HSC GENERAL EXAM "
            "HALL TICKET NOV-DEC-2026 GSOS SSC Exam"
        )
        self.assertTrue(is_navigation_noise_title(title))

    def test_keeps_a_long_single_exam_notice(self):
        from check import is_navigation_noise_title
        title = (
            "Gujarat Board announces the revised examination timetable for the 2027 "
            "Higher Secondary School Certificate examination, including subject-wise "
            "dates, reporting instructions and hall-ticket information for candidates."
        )
        self.assertFalse(is_navigation_noise_title(title))

    def test_rejects_old_year_only_notice_from_latest_feed(self):
        self.assertTrue(is_stale_notice(
            "Railway Recruitment Cell Notice for Re-medical of candidates CEN02 of 2018"
        ))

    def test_keeps_recent_exam_year_notice(self):
        self.assertFalse(is_stale_notice(
            "UP Police Constable Score Card 2026"
        ))

    def test_rejects_old_year_in_archive_url_even_when_title_is_generic(self):
        self.assertTrue(is_stale_notice(
            "Timetable",
            "",
            "https://www.pondiuni.edu.in/old-results/2020/timetable.pdf",
        ))

    def test_keeps_current_year_in_official_notice_url(self):
        self.assertFalse(is_stale_notice(
            "Timetable",
            "",
            "https://www.example.edu.in/notices/2026/timetable.pdf",
        ))

    def test_ignores_unrelated_cultural_event(self):
        self.assertIsNone(classify("Annual Cultural Festival 2026"))

    def test_keeps_exam_results_in_official_press_releases(self):
        self.assertEqual(classify("Press Release: CBSE Declares Class X Result 2026"), "result")

    def test_rejects_editorial_placeholder_not_official_notice(self):
        self.assertTrue(
            is_speculative_status_title("IBPS PO/MT-XVI Mains Result 2026 — Awaiting Official Update")
        )
        self.assertFalse(
            is_speculative_status_title("IBPS PO/MT-XVI Mains Result 2026")
        )

    def test_old_explicit_feed_date_is_stale(self):
        self.assertTrue(is_stale_notice("Recruitment Result", "Mon, 01 Jan 2024 00:00:00 GMT"))

    def test_current_feed_date_is_not_stale(self):
        self.assertFalse(is_stale_notice("Recruitment Result", "Fri, 16 Oct 2026 09:00:00 GMT"))

    def test_old_uploaded_date_in_notice_title_is_stale(self):
        self.assertTrue(is_stale_notice("Result uploaded on 13/02/2024", ""))

    def test_old_unlabelled_date_at_end_of_title_is_stale(self):
        self.assertTrue(is_stale_notice("Most Urgent Public Notice 22/02/2023", ""))

    def test_old_iso_date_in_notice_title_is_stale(self):
        self.assertTrue(is_stale_notice("2026-06-25 ODISHA STATE OPEN SCHOOL EXAM ADMIT CARD", ""))

    def test_old_compact_date_in_official_pdf_url_is_stale(self):
        self.assertTrue(is_stale_notice(
            "Press Release: CBSE Post-Result Portal Notice",
            "",
            "https://www.cbse.gov.in/cbsenew/documents/Press_Release_Complaint_PVR_05062026.pdf",
        ))

    def test_current_unlabelled_full_date_is_not_stale(self):
        self.assertFalse(is_stale_notice("Notice issued 01 Nov 2026", ""))

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

    def test_navigation_menu_clusters_are_rejected(self):
        from check import is_navigation_noise_title
        self.assertTrue(is_navigation_noise_title(
            "Services Pay Fee Online For Offline Applications KU Mail Official e-Mail Service Jobs/Recruitment Advertisements,Call Letters Tenders Notices,eTenders Employee Online Services Downloads Forms Applications Photogallery Conferences Workshops"
        ))
        self.assertTrue(is_navigation_noise_title(
            "e-PRATIKAAR e-Samikshya Virtual Tour e-Learning e-Admission Results Examinations Online Payment PM Internship Scheme 2025 Library Seminars Conferences"
        ))
        self.assertTrue(is_navigation_noise_title("Jobs/Recruitment Advertisements,Call Letters"))
        self.assertTrue(is_navigation_noise_title(
            "Home Current Vacancies Vacancies Call Letters Results Recruitment Calendar "
            "Summer Placements Research Internship Scholarships Post based Rosters"
        ))
        self.assertFalse(is_navigation_noise_title("SSC CGL Tier-I Result 2026"))
        self.assertIsNone(classify("Date Sheet"))
        self.assertIsNone(classify("Examination Notice Board"))
        self.assertIsNone(classify("RESULTS & Statistics Results Statistics"))
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
            "RTI Policy Information RTI Officers JPSC Resolution Public Notice RTI Related Case Decisions",
            "Information RTI Officers JPSC Resolution Public Notice",
        ):
            with self.subTest(title=title):
                self.assertIsNone(
                    classify_source_title(title, {"include_all_items": True})
                )


    def test_transient_connection_reset_is_retried(self):
        from unittest.mock import patch
        import requests

        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        with patch("check.requests.get", side_effect=[requests.ConnectionError("connection reset by peer"), response]) as mocked, patch("check.time.sleep"):
            self.assertEqual(get_with_retries("https://example.gov.in/").status_code, 200)
            self.assertEqual(mocked.call_count, 2)

    def test_tls_failure_retries_with_verified_system_ca_bundle(self):
        from unittest.mock import patch
        import requests

        response = requests.Response()
        response.status_code = 200
        response._content = b"verified"
        with patch("check.os.path.isfile", return_value=True), patch(
            "check.requests.get",
            side_effect=[
                requests.exceptions.SSLError("CERTIFICATE_VERIFY_FAILED"),
                response,
            ],
        ) as mocked:
            self.assertEqual(get_with_retries("https://example.gov.in/").text, "verified")
            self.assertEqual(mocked.call_count, 2)
            self.assertEqual(
                mocked.call_args.kwargs["verify"],
                "/etc/ssl/certs/ca-certificates.crt",
            )


    def test_temporary_dns_failure_is_retried(self):
        from unittest.mock import patch
        import requests

        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        with patch("check.requests.get", side_effect=[
            requests.ConnectionError("NameResolutionError temporary DNS failure"),
            response,
        ]) as mocked, patch("check.time.sleep"):
            self.assertEqual(get_with_retries("https://example.gov.in/").status_code, 200)
            self.assertEqual(mocked.call_count, 2)

    def test_source_timeout_is_bounded_for_scheduled_scans(self):
        from unittest.mock import patch
        import requests

        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        with patch("check.requests.get", return_value=response) as mocked:
            get_with_retries("https://example.gov.in/")
            timeout = mocked.call_args.kwargs["timeout"]
            self.assertGreater(timeout[0], 0)
            self.assertGreater(timeout[1], 0)
            self.assertLessEqual(timeout[0], 20)
            self.assertLessEqual(timeout[1], 25)
            self.assertGreaterEqual(timeout[0], 5)
            self.assertGreaterEqual(timeout[1], 5)


    def test_rejects_long_concatenated_homepage_content(self):
        from check import is_navigation_noise_title
        title = (
            "Intimation regarding Principals and Management Meeting on 4th November 2026 "
            "at JNTUH. FullTime Ph.D. and PDF Admissions under the Visvesvaraya Scheme: "
            "List of Eligible Candidates, Interview Schedule, and Instructions. "
            "Google Developer Group activities, campus news and other links."
        )
        self.assertTrue(is_navigation_noise_title(title))

    def test_keeps_a_legitimate_detailed_notice_title(self):
        from check import is_navigation_noise_title
        self.assertFalse(is_navigation_noise_title(
            "Notification for recruitment to the post of Junior Engineer "
            "including eligibility, application dates and examination schedule"
        ))

    def test_rejects_concatenated_commission_notice_menu(self):
        from check import is_navigation_noise_title
        self.assertTrue(is_navigation_noise_title(
            "Notification for Screening/Written Examination Notification for "
            "Personal Interview Notification for Answer Keys Notification for "
            "Viewing Marks Corrigendum/Addendum"
        ))

    def test_rejects_concatenated_university_navigation(self):
        from check import is_navigation_noise_title
        self.assertTrue(is_navigation_noise_title(
            "CET 2025 Notices CET 2025 Results Management Quota Admission "
            "Regulatory Committee Refund Policy Refund Status Admission 2024"
        ))

    def test_rejects_recruitment_menu_not_a_notice(self):
        from check import is_navigation_noise_title
        self.assertTrue(is_navigation_noise_title(
            "Recruitment Process Instructions to Applicants Apply for Job"
        ))

    def test_upsc_whats_new_concatenated_menu_cluster_is_rejected(self):
        from check import is_navigation_noise_title
        title = (
            "Status of Lateral Recruitment Cases (Advertisement-wise) "
            "Applicants' List Notices Corrigendum Scrutiny Interview Schedules "
            "Results Marks Information open_in_new Recruitment cases kept on hold "
            "on account of Pending Litigations"
        )
        self.assertTrue(is_navigation_noise_title(title))

    def test_upsc_generic_navigation_destinations_are_not_exam_notices(self):
        from check import is_navigation_noise_title
        for title in ("Corrigendum", "Result Details", "Provisional Answer Key",
                      "Applicants' List", "Interview Schedules"):
            with self.subTest(title=title):
                self.assertTrue(is_navigation_noise_title(title))
        self.assertFalse(is_navigation_noise_title("Corrigendum to NDA Result 2026"))

    def test_rejects_portal_menu_cluster_with_repeated_external_link_labels(self):
        from check import is_navigation_noise_title
        title = ("Recruitment Tests Schedule for Recruitment Tests and Interviews Notice "
                 "e-admit Card open_in_new Results Cut-off Marks Result Details Answer Keys "
                 "Marks Information open_in_new Question Papers Provisional Answer Key")
        self.assertTrue(is_navigation_noise_title(title))

    def test_published_results_preserve_distinct_sbi_official_urls(self):
        records = [
            {"id": "first", "title": "RECRUITMENT OF SPECIALIST CADRE OFFICER", "source_name": "SBI Current Openings", "category": "notification", "url": "https://sbi.co.in/careers/one"},
            {"id": "duplicate", "title": "Recruitment of Specialist Cadre Officer", "source_name": "State Bank of India Recruitment", "category": "notification", "url": "https://sbi.co.in/careers/two"},
            {"id": "different-category", "title": "Recruitment of Specialist Cadre Officer", "source_name": "SBI Current Openings", "category": "result", "url": "https://sbi.co.in/careers/three"},
        ]
        cleaned = deduplicate_published_results(records)
        self.assertEqual([item["id"] for item in cleaned], ["first", "duplicate", "different-category"])

    def test_published_results_deduplicate_different_registry_labels_on_same_host(self):
        records = [
            {"id": "first", "title": "JEE Main Session 1 Admit Card 2026", "source_name": "JEE Main", "category": "admit_card", "url": "https://jeemain.nta.nic.in/admit-card"},
            {"id": "duplicate", "title": "JEE Main Session 1 Admit Card 2026", "source_name": "JEE Main public notices and results", "category": "admit_card", "url": "https://www.jeemain.nta.nic.in/admit-card?utm_source=telegram"},
            {"id": "different-category", "title": "JEE Main Session 1 Admit Card 2026", "source_name": "JEE Main", "category": "result", "url": "https://jeemain.nta.nic.in/result"},
        ]
        cleaned = deduplicate_published_results(records)
        self.assertEqual([item["id"] for item in cleaned], ["first", "different-category"])

    def test_notice_title_normalization_preserves_unicode_and_ignores_freshness_words(self):
        self.assertEqual(
            normalize_notice_title("Latest — परीक्षा Result 2026"),
            normalize_notice_title("परीक्षा Result 2026")
        )

    def test_sbi_sco_biodata_attachment_is_not_a_separate_alert(self):
        from check import is_auxiliary_sbi_attachment
        item = {
            "source_id": "sbi-current-openings",
            "source_name": "SBI Current Openings",
            "title": "RECRUITMENT OF SPECIALIST CADRE OFFICER ON REGULAR BASIS "
                     "ADVERTISEMENT NO: CRPD/SCO/2026-27/31",
            "url": "https://sbi.bank.in/documents/20112026_BIODATA_SCO-31.pdf",
        }
        self.assertTrue(is_auxiliary_sbi_attachment(item))
        item["url"] = "https://sbi.bank.in/documents/20112026_Final_ADV_CRPD_SCO_31.pdf"
        self.assertFalse(is_auxiliary_sbi_attachment(item))
        item["source_id"] = "other-authority"
        item["url"] = "https://other.gov.in/biodata.pdf"
        self.assertFalse(is_auxiliary_sbi_attachment(item))

    def test_same_title_different_official_urls_are_preserved(self):
        records = [
            {"id": "first", "title": "UPSC Recruitment Test Schedule 2026", "source_name": "UPSC", "category": "exam_schedule", "url": "https://upsc.gov.in/notices/one"},
            {"id": "second", "title": " UPSC Recruitment Test Schedule 2026 ", "source_name": "UPSC", "category": "exam_schedule", "url": "https://upsc.gov.in/notices/two"},
            {"id": "alias-third", "title": "UPSC Recruitment Test Schedule 2026", "source_name": "UPSC Active Examinations and notices", "category": "exam_schedule", "url": "https://upsc.gov.in/notices/three"},
            {"id": "different", "title": "UPSC Civil Services Result 2026", "source_name": "UPSC", "category": "result", "url": "https://upsc.gov.in/notices/four"},
            {"id": "other-authority", "title": "UPSC Recruitment Test Schedule 2026", "source_name": "State PSC", "category": "exam_schedule", "url": "https://statepsc.gov.in/notices/one"},
        ]
        cleaned = deduplicate_published_results(records)
        self.assertEqual([item["id"] for item in cleaned], ["first", "second", "alias-third", "different", "other-authority"])



if __name__ == "__main__":
    unittest.main()
