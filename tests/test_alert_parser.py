"""Tests for the job-alert digest parser.

Fixtures are real message bodies, trimmed only of tracking-parameter tails.
The parser must never invent a field: a listing it cannot read is a listing
it must skip, not one it guesses at.
"""
import base64
import pathlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.alert_parser import parse, rank, dedupe  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def linkedin():
    return parse((FIXTURES / "linkedin_digest.txt").read_text(),
                 "jobalerts-noreply@linkedin.com")


class ParserTests(unittest.TestCase):


    def test_extracts_every_listing_not_just_the_subject_one(self):
        # The subject named only "Staff Applied Scientist, Trust".
        self.assertEqual(len(linkedin()), 6)


    def test_fields_are_read_not_guessed(self):
        first = linkedin()[0]
        self.assertEqual(first["title"], "Staff Applied Scientist, Trust")
        self.assertEqual(first["company"], "LinkedIn")
        self.assertEqual(first["location"], "Mountain View, CA")
        self.assertEqual(first["job_id"], "4458252621")
        self.assertEqual(first["source"], "linkedin")


    def test_url_is_stripped_of_tracking_but_still_resolves(self):
        url = linkedin()[0]["url"]
        self.assertEqual(url, "https://www.linkedin.com/jobs/view/4458252621/")
        self.assertNotIn("trackingId", url); self.assertNotIn("midToken", url)


    def test_footer_and_see_all_links_are_not_listings(self):
        titles = [x["title"] for x in linkedin()]
        self.assertFalse(any("See all jobs" in t for t in titles))
        self.assertFalse(any("Unsubscribe" in t for t in titles))
        self.assertFalse(any("LinkedIn Corporation" in t for t in titles))


    def test_dedupe_is_by_job_id_not_title(self):
        a = {"job_id": "1", "title": "SWE", "source": "linkedin", "first_seen": "2026-08-25"}
        b = {"job_id": "1", "title": "SWE - Toronto", "source": "linkedin", "first_seen": "2026-08-27"}
        c = {"job_id": "2", "title": "SWE", "source": "linkedin", "first_seen": "2026-08-27"}
        out = dedupe([a, b, c])
        self.assertEqual(len(out), 2)
        # earliest sighting wins; a listing is not "new" because it was resent
        self.assertEqual(next(x for x in out if x["job_id"] == "1")["first_seen"], "2026-08-25")


    def facet(self):
        from agents.alert_parser import parse as _parse
        return _parse((FIXTURES / "linkedin_facet.txt").read_text(),
                      "jobs-noreply@linkedin.com")

    def test_rank_puts_local_new_grad_first(self):
        ranked = rank(linkedin() + self.facet(),
                      ["software engineer", "new grad", "remote"], home="ON")
        self.assertIn("New Grad", ranked[0]["title"])
        self.assertNotEqual(ranked[0]["company"], "LinkedIn")

    def test_every_senior_us_listing_ranks_below_every_local_junior_one(self):
        """The real digest is six senior Bay Area / NY roles; the facet fixture
        is six Toronto-area junior ones. Seniority and location must sink all
        six of the former, however well their titles match on keywords."""
        digest_titles = {x["title"] for x in linkedin()}
        ranked = rank(linkedin() + self.facet(),
                      ["software engineer", "engineer", "new grad"], home="ON")
        bottom_six = {x["title"] for x in ranked[-6:]}
        self.assertEqual(bottom_six, digest_titles)


class FacetTemplateTests(unittest.TestCase):
    """A second real LinkedIn template. The subject named one job of six."""

    def facet(self):
        from agents.alert_parser import parse_report
        return parse_report((FIXTURES / "linkedin_facet.txt").read_text(),
                            "jobs-noreply@linkedin.com")

    def test_finds_all_six_not_the_one_in_the_subject(self):
        r = self.facet()
        self.assertEqual(len(r["listings"]), 6)
        self.assertEqual(r["unreadable"], 0)

    def test_badge_lines_do_not_shift_the_fields(self):
        # "Fast growing" sits exactly where the location would be.
        zip_row = next(x for x in self.facet()["listings"] if x["company"] == "Zip")
        self.assertEqual(zip_row["title"], "Software Engineer, New Grad (2027 Start)")
        self.assertEqual(zip_row["location"], "Toronto")

    def test_section_headers_are_not_titles(self):
        titles = [x["title"] for x in self.facet()["listings"]]
        for junk in ("Remote jobs", "Fintech jobs", "LLM jobs", "Expand your search"):
            self.assertNotIn(junk, titles)

    def test_hidden_toronto_roles_are_recovered(self):
        got = {(x["company"], x["title"]) for x in self.facet()["listings"]}
        self.assertIn(("TD", "Associate Software Engineer"), got)
        self.assertIn(("Scotiabank", "Junior Software Engineer"), got)
        self.assertIn(("FGF Brands", "AI Engineer - New Grad"), got)


class IndeedTests(unittest.TestCase):
    """Indeed's layout shares nothing with LinkedIn's, and its job keys arrive
    mangled by quoted-printable decoding."""

    def indeed(self):
        from agents.alert_parser import parse_report
        return parse_report((FIXTURES / "indeed_digest.txt").read_text(),
                            "donotreply@jobalert.indeed.com")

    def test_reads_every_listing_in_the_fixture(self):
        self.assertEqual(len(self.indeed()["listings"]), 6)

    def test_company_and_location_split_on_the_last_dash(self):
        # The title itself contains " - "; only the second line may be split.
        row = next(x for x in self.indeed()["listings"]
                   if x["title"].startswith("2027 Winter - ECCO"))
        self.assertEqual(row["company"], "Royal Bank of Canada")
        self.assertEqual(row["location"], "Toronto, ON")

    def test_mangled_job_key_is_reconstructed(self):
        row = next(x for x in self.indeed()["listings"]
                   if x["title"].startswith("2027 Winter - ECCO"))
        # "=10" was decoded to \x10 in transit; the real key starts "10".
        self.assertEqual(row["job_id"], "10762b9150fc2b52")
        self.assertEqual(row["url"], "https://ca.indeed.com/viewjob?jk=10762b9150fc2b52")

    def test_every_job_id_is_sixteen_hex_chars(self):
        import re as _re
        for x in self.indeed()["listings"]:
            self.assertRegex(x["job_id"], r"^[0-9a-f]{16}$")

    def test_salary_is_read_when_present_and_absent_otherwise(self):
        rows = {x["company"]: x for x in self.indeed()["listings"]}
        self.assertEqual(rows["BMO Financial Group"]["salary"], "$45,500\u2013$84,500 a year")
        self.assertIsNone(rows["Scotiabank"]["salary"])

    def test_sponsored_ad_without_a_job_key_is_counted_not_invented(self):
        r = self.indeed()
        titles = [x["title"] for x in r["listings"]]
        self.assertNotIn("Night Building Assistant", titles)
        self.assertEqual(r["unreadable"], 1)

    def test_header_and_footer_are_not_listings(self):
        titles = [x["title"] for x in self.indeed()["listings"]]
        for junk in ("Indeed Job Alert", "Do not share this email", "Jobs 1-16 of 16 new jobs"):
            self.assertNotIn(junk, titles)

    def test_a_correctly_escaped_key_is_not_reversed(self):
        # Real 2026-08-30 digests: Indeed's template escaped the "=" properly
        # this time, so the decoded body already carries the true 16-hex key
        # after a literal "=". Applying the mangled-byte reversal here would
        # prepend a fake "3d" and drop the real trailing two digits — exactly
        # the corruption a subagent caught before it reached listings_email.json.
        from agents.alert_parser import parse_indeed
        body = ("Software Engineer @ Autodesk\r\n"
                "Autodesk - Toronto, ON\r\n"
                "Just posted\r\n"
                "https://ca.indeed.com/rc/clk/dl?jk=7e7c5ff656671269&from=ja\r\n")
        rows = parse_indeed(body, "2026-08-30")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["job_id"], "7e7c5ff656671269")

    def test_a_mangled_key_starting_with_hex_3d_still_reverses_correctly(self):
        # ord('=') is 0x3d, so a genuinely mangled marker byte can itself
        # decode to a literal "=" — indistinguishable from the clean case by
        # character alone. True key "3d84c15b2a9165af": the encoder's bug
        # drops "3d" into the decoder's escape, leaving "=" plus only the
        # other 14 hex digits, which is what disambiguates it from a clean
        # (16-digit) match.
        from agents.alert_parser import parse_indeed
        body = ("Data Analyst Intern\r\n"
                "Shopify - Ottawa, ON\r\n"
                "Just posted\r\n"
                "https://ca.indeed.com/rc/clk/dl?jk=84c15b2a9165af&from=ja\r\n")
        rows = parse_indeed(body, "2026-08-30")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["job_id"], "3d84c15b2a9165af")


def _raw_indeed_message(body_text: str) -> str:
    """Build a base64url RFC 2822 message the way Gmail's RAW format would,
    with `body_text` inserted as an already quoted-printable-*encoded*
    payload — i.e. the caller controls exactly what stays undecoded, which is
    the point: real Indeed digests leave `jk=<hex>` unescaped, and the test
    fixtures below reproduce that literally rather than via `quopri.encode`,
    which would (correctly) escape the `=` and never trigger the bug."""
    msg = ("From: donotreply@jobalert.indeed.com\r\n"
           "To: user@example.com\r\n"
           "Subject: Test\r\n"
           "Content-Type: text/plain; charset=utf-8\r\n"
           "Content-Transfer-Encoding: quoted-printable\r\n"
           "\r\n" + body_text)
    return base64.urlsafe_b64encode(msg.encode("ascii")).decode("ascii")


class IndeedRawTests(unittest.TestCase):
    """The job key mangled by quoted-printable decoding (IndeedTests, above)
    can only be reversed because a byte survived intact from Gmail's tool
    output into a Python string. A byte that is an invalid lone surrogate or
    an unprintable control character does not reliably survive that trip
    through a text-generation interface — so the real fix fetches the
    message before decoding runs at all, when the job key is still literal
    ASCII. These tests exercise that path directly, independent of Gmail."""

    def test_job_id_recovered_from_undecoded_source(self):
        from agents.alert_parser import extract_indeed_raw

        body = ("2027 Winter - ECCO, Data Intern (4 Months)\r\n"
                "Royal Bank of Canada - Toronto, ON\r\n"
                "Just posted\r\n"
                "https://ca.indeed.com/rc/clk/dl?jk=10762b9150fc2b52&from=ja\r\n")
        decoded, job_ids = extract_indeed_raw(_raw_indeed_message(body))
        self.assertEqual(job_ids, ["10762b9150fc2b52"])
        self.assertIn("2027 Winter - ECCO, Data Intern (4 Months)", decoded)

    def test_soft_line_break_across_the_job_key_is_unwrapped_first(self):
        from agents.alert_parser import extract_indeed_raw
        # A real 76-column QP wrap could land the trailing soft break inside
        # the hex run; unwrapping must happen before the key is read out.
        body = ("Title\r\nCompany - City\r\nJust posted\r\n"
                "https://ca.indeed.com/rc/clk/dl?jk=1076=\r\n2b9150fc2b52&from=ja\r\n")
        _, job_ids = extract_indeed_raw(_raw_indeed_message(body))
        self.assertEqual(job_ids, ["10762b9150fc2b52"])

    def test_end_to_end_produces_the_same_listing_as_the_byte_reversal_path(self):
        from agents.alert_parser import extract_indeed_raw, parse_indeed
        body = ("2027 Winter - ECCO, Data Intern (4 Months)\r\n"
                "Royal Bank of Canada - Toronto, ON\r\n"
                "Just posted\r\n"
                "https://ca.indeed.com/rc/clk/dl?jk=10762b9150fc2b52&from=ja\r\n")
        decoded, job_ids = extract_indeed_raw(_raw_indeed_message(body))
        rows = parse_indeed(decoded, "2026-08-30", raw_job_ids=job_ids)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["job_id"], "10762b9150fc2b52")
        self.assertEqual(rows[0]["url"], "https://ca.indeed.com/viewjob?jk=10762b9150fc2b52")

    def test_no_text_plain_part_yields_nothing_not_a_crash(self):
        from agents.alert_parser import extract_indeed_raw
        msg = ("From: a@b.com\r\nTo: c@d.com\r\nSubject: x\r\n"
               "Content-Type: text/html\r\n\r\n<p>hi</p>")
        raw = base64.urlsafe_b64encode(msg.encode("ascii")).decode("ascii")
        decoded, job_ids = extract_indeed_raw(raw)
        self.assertEqual((decoded, job_ids), ("", []))

    def test_garbage_input_yields_nothing_not_a_crash(self):
        from agents.alert_parser import extract_indeed_raw
        self.assertEqual(extract_indeed_raw("not valid base64!!!"), ("", []))

    def test_report_wrapper_matches_parse_report_shape(self):
        from agents.alert_parser import parse_indeed_raw_report
        body = ("2027 Winter - ECCO, Data Intern (4 Months)\r\n"
                "Royal Bank of Canada - Toronto, ON\r\n"
                "Just posted\r\n"
                "https://ca.indeed.com/rc/clk/dl?jk=10762b9150fc2b52&from=ja\r\n")
        r = parse_indeed_raw_report(_raw_indeed_message(body), "2026-08-30")
        self.assertTrue(r["parser"])
        self.assertEqual(r["source"], "indeed")
        self.assertEqual(len(r["listings"]), 1)


class Jobs2WebTests(unittest.TestCase):
    """jobs2web (SAP SuccessFactors) renders through at least two templates
    depending on the employer: Capgemini/TELUS give each listing a real
    markdown link; Scotiabank/Rogers wrap an empty link after plain text,
    with every listing packed into one paragraph with no line breaks."""

    def scotiabank(self):
        from agents.alert_parser import parse_report
        return parse_report((FIXTURES / "jobs2web_scotiabank_digest.txt").read_text(),
                            "scotiabank-jobnotification@noreply17.jobs2web.com")

    def capgemini(self):
        from agents.alert_parser import parse_report
        return parse_report((FIXTURES / "jobs2web_capgemini_digest.txt").read_text(),
                            "capgemitecp3-jobnotification@noreply12.jobs2web.com")

    def telus(self):
        from agents.alert_parser import parse_report
        return parse_report((FIXTURES / "jobs2web_telus_digest.txt").read_text(),
                            "TELUS_job_alerts@noreply17.jobs2web.com")

    def rogers(self):
        from agents.alert_parser import parse_report
        return parse_report((FIXTURES / "jobs2web_rogers_digest.txt").read_text(),
                            "rogers-jobnotification@noreply.jobs2web.com")

    def test_reads_every_listing_in_each_template(self):
        self.assertEqual(len(self.scotiabank()["listings"]), 10)
        self.assertEqual(len(self.capgemini()["listings"]), 10)
        self.assertEqual(len(self.telus()["listings"]), 10)
        self.assertEqual(len(self.rogers()["listings"]), 10)

    def test_intro_chrome_does_not_leak_into_the_first_title(self):
        # Real bug: Scotiabank's blob has no link between the greeting and
        # the first listing, so a naive split left ". Jobs" glued to the
        # title; Rogers has the same problem via a bare colon instead.
        first_scotia = self.scotiabank()["listings"][0]
        self.assertEqual(first_scotia["title"],
                         "Technical Analyst Advisory (Capital Markets Technology)")
        first_rogers = self.rogers()["listings"][0]
        self.assertEqual(first_rogers["title"], "Sr Mgr, Fraud Strategy")

    def test_titles_with_their_own_dashes_still_split_correctly(self):
        row = next(x for x in self.scotiabank()["listings"]
                   if x["job_id"] == "605642017")
        self.assertEqual(row["title"], "Senior Payroll Analyst (12-month contract)")
        self.assertEqual(row["location"], "Scarborough, ON, CA, M1L4S2")

    def test_location_without_a_province_code_is_still_recognized(self):
        # Capgemini's template omits the province entirely ("Mississauga, CA").
        row = self.capgemini()["listings"][0]
        self.assertEqual(row["location"], "Mississauga, CA")

    def test_company_comes_from_the_sender_not_the_body(self):
        for row in self.telus()["listings"]:
            self.assertEqual(row["company"], "TELUS")
        for row in self.rogers()["listings"]:
            self.assertEqual(row["company"], "Rogers Communications")

    def test_job_id_is_the_trailing_digits_in_the_job_url(self):
        row = self.capgemini()["listings"][0]
        self.assertEqual(row["job_id"], "1429357433")

    def test_unknown_tenant_is_counted_not_guessed(self):
        from agents.alert_parser import parse_report
        body = "[Some Role - Waterloo, ON, CA](http://jobs.example.com/job/x/12345/)"
        r = parse_report(body, "somebank-jobnotification@noreply.jobs2web.com")
        self.assertEqual(r["listings"], [])
        self.assertEqual(r["unreadable"], 1)

    def test_a_tracking_query_string_after_the_id_does_not_hide_the_listing(self):
        # Real bug: production links carry "?from=email&refid=..." after the
        # job id; the fixtures used to build this were trimmed of exactly
        # that tail, so an end-anchored id regex passed every test while
        # matching zero real listings.
        from agents.alert_parser import parse_report
        body = ("[Data Analyst - Waterloo, ON, CA]"
                "(http://jobs.scotiabank.com/job/Waterloo-Data-Analyst-ON/605642099/"
                "?from=email&amp;refid=abc123&amp;eid=9)")
        r = parse_report(body, "scotiabank-jobnotification@noreply17.jobs2web.com")
        self.assertEqual(len(r["listings"]), 1)
        self.assertEqual(r["listings"][0]["job_id"], "605642099")


class JobrightTests(unittest.TestCase):
    """Jobright's PLAIN_TEXT body drops all listing content — it only
    survives in the HTML, keyed by element id rather than layout."""

    def jobright(self):
        from agents.alert_parser import parse_jobright_report
        return parse_jobright_report(
            (FIXTURES / "jobright_digest.html").read_text(), "2026-08-29")

    def test_reads_every_card_in_the_fixture(self):
        self.assertEqual(len(self.jobright()["listings"]), 10)

    def test_fields_come_from_their_own_tagged_elements_not_layout(self):
        row = next(x for x in self.jobright()["listings"]
                   if x["job_id"] == "69e8fc294b0fa35a7076a8f6")
        self.assertEqual(row["title"], "Software Engineer II, Backend (PMI Integrations)")
        self.assertEqual(row["company"], "Affirm")
        self.assertEqual(row["location"], "Remote")
        self.assertEqual(row["salary"], "$125K/yr - $175K/yr")
        self.assertEqual(row["posted"], "3 hours ago")

    def test_a_referral_count_tag_is_not_mistaken_for_location_or_salary(self):
        row = next(x for x in self.jobright()["listings"]
                   if x["job_id"] == "6a7f4a35b56bea5779c09e86")
        self.assertEqual(row["location"], "Toronto, ON")
        self.assertIsNone(row["salary"])

    def test_a_card_missing_from_its_own_wrapper_table_does_not_leak_fields(self):
        # The card-boundary regex must not let one listing's table swallow
        # the next listing's fields when scanning for id="job-section".
        rows = self.jobright()["listings"]
        titles = {r["job_id"]: r["title"] for r in rows}
        self.assertEqual(titles["6a91fd053603630099195786"],
                         "Associate Product Support Specialist")
        self.assertEqual(titles["6a594ef24da96a42cfd907d4"], "Sales Associate")


class RecencyTests(unittest.TestCase):
    def test_indeed_age_line_is_captured(self):
        from agents.alert_parser import parse
        rows = parse((FIXTURES / "indeed_digest.txt").read_text(),
                     "donotreply@jobalert.indeed.com", "2026-08-25")
        ages = {x["company"]: x["posted"] for x in rows}
        self.assertEqual(ages["TD Bank"], "1 day ago")
        self.assertEqual(ages["Scotiabank"], "Just posted")

    def test_age_days_reads_the_posted_line_before_the_email_date(self):
        from agents.alert_parser import age_days
        self.assertEqual(age_days({"posted": "Just posted"}), 0.0)
        self.assertEqual(age_days({"posted": "6 days ago"}), 6.0)
        # email date is only the fallback
        self.assertEqual(
            age_days({"posted": None, "first_seen": "2026-08-20"}, "2026-08-27"), 7.0)

    def test_workday_phrasing_is_understood_too(self):
        from agents.alert_parser import age_days
        self.assertEqual(age_days({"posted": "Posted Today"}), 0.0)
        self.assertEqual(age_days({"posted": "Posted Yesterday"}), 1.0)
        self.assertEqual(age_days({"posted": "Posted 2 Days Ago"}), 2.0)
        self.assertEqual(age_days({"posted": "Posted 30+ Days Ago"}), 30.0)

    def test_unknown_age_is_not_treated_as_fresh(self):
        from agents.alert_parser import age_days, score
        self.assertIsNone(age_days({"posted": None, "first_seen": None}))
        base = {"title": "Software Engineer", "location": "Toronto"}
        unknown = score(dict(base, posted=None, first_seen=None), [], today="2026-08-27")
        fresh = score(dict(base, posted="Just posted"), [], today="2026-08-27")
        self.assertLess(unknown, fresh)

    def test_stale_listing_ranks_below_an_otherwise_equal_fresh_one(self):
        from agents.alert_parser import rank
        a = {"title": "Junior Software Engineer", "location": "Toronto",
             "company": "A", "posted": "Just posted"}
        b = {"title": "Junior Software Engineer", "location": "Toronto",
             "company": "B", "posted": "30 days ago"}
        self.assertEqual(rank([b, a], ["software engineer"], today="2026-08-27")[0]["company"], "A")


class CrossSourceTests(unittest.TestCase):
    """One role arriving from several sources must appear once — without ever
    merging two roles that are merely similar."""

    def idx(self):
        import json
        from agents.alert_parser import build_alias_index
        cfg = json.loads(pathlib.Path("config/ats_sources.json").read_text())
        return build_alias_index(cfg["tenants"])

    def test_same_role_from_linkedin_and_workday_collapses_once(self):
        from agents.alert_parser import collapse_across_sources
        rows = [
            {"title": "Associate Software Engineer", "company": "Royal Bank of Canada",
             "source": "linkedin", "job_id": "1", "url": "li", "first_seen": "2026-08-26"},
            {"title": "Associate Software Engineer", "company": "RBC",
             "source": "workday:rbc", "job_id": "R-1", "url": "wd", "first_seen": "2026-08-27"},
        ]
        out = collapse_across_sources(rows, self.idx())
        self.assertEqual(len(out), 1)
        # the employer's own posting is canonical
        self.assertEqual(out[0]["url"], "wd")
        self.assertEqual(out[0]["also_on"], ["linkedin"])
        # earliest sighting survives
        self.assertEqual(out[0]["first_seen"], "2026-08-26")

    def test_punctuation_and_case_differences_still_collapse(self):
        from agents.alert_parser import collapse_across_sources
        rows = [{"title": "Software Engineer, New Grad (2027 Start)", "company": "Zip",
                 "source": "linkedin", "job_id": "1"},
                {"title": "software engineer - new grad 2027 start", "company": "Zip",
                 "source": "workday:zip", "job_id": "2"}]
        self.assertEqual(len(collapse_across_sources(rows, self.idx())), 1)

    def test_similar_but_different_titles_do_not_merge(self):
        """A wrong merge hides a real job; a missed merge only shows a
        duplicate. The conservative error is the correct one."""
        from agents.alert_parser import collapse_across_sources
        rows = [{"title": "Lead Full Stack Developer", "company": "RBC",
                 "source": "workday:rbc", "job_id": "R-1"},
                {"title": "Lead Full Stack Developer - Python", "company": "RBC",
                 "source": "workday:rbc", "job_id": "R-2"}]
        self.assertEqual(len(collapse_across_sources(rows, self.idx())), 2)

    def test_same_title_at_different_employers_does_not_merge(self):
        from agents.alert_parser import collapse_across_sources
        rows = [{"title": "Junior Software Engineer", "company": "Scotiabank",
                 "source": "linkedin", "job_id": "1"},
                {"title": "Junior Software Engineer", "company": "BMO",
                 "source": "linkedin", "job_id": "2"}]
        self.assertEqual(len(collapse_across_sources(rows, self.idx())), 2)

    def test_same_title_within_one_source_is_never_merged(self):
        """RBC posts five separate 'Senior Data Engineer' requisitions. They
        share a title and differ only by req id; merging them would delete
        four real jobs."""
        from agents.alert_parser import collapse_across_sources
        rows = [{"title": "Senior Data Engineer", "company": "RBC",
                 "source": "workday:rbc", "job_id": f"R-{i}"} for i in range(5)]
        self.assertEqual(len(collapse_across_sources(rows, self.idx())), 5)

    def test_ambiguous_cross_source_match_is_left_alone(self):
        """Two same-title postings at one employer plus one from elsewhere:
        which pairs with which is unknowable, so nothing is merged."""
        from agents.alert_parser import collapse_across_sources
        rows = [{"title": "Lead Platform Engineer", "company": "RBC",
                 "source": "workday:rbc", "job_id": "R-1"},
                {"title": "Lead Platform Engineer", "company": "RBC",
                 "source": "workday:rbc", "job_id": "R-2"},
                {"title": "Lead Platform Engineer", "company": "Royal Bank of Canada",
                 "source": "linkedin", "job_id": "L-1"}]
        self.assertEqual(len(collapse_across_sources(rows, self.idx())), 3)

    def test_unlisted_alias_fails_safe_as_a_duplicate(self):
        from agents.alert_parser import collapse_across_sources
        rows = [{"title": "Data Analyst", "company": "Some Bank Nobody Listed",
                 "source": "linkedin", "job_id": "1"},
                {"title": "Data Analyst", "company": "SBNL",
                 "source": "workday:sbnl", "job_id": "2"}]
        # visible duplicate, not a silent merge
        self.assertEqual(len(collapse_across_sources(rows, self.idx())), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
