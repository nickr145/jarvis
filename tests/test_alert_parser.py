"""Tests for the job-alert digest parser.

Fixtures are real message bodies, trimmed only of tracking-parameter tails.
The parser must never invent a field: a listing it cannot read is a listing
it must skip, not one it guesses at.
"""
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
