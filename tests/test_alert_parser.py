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


if __name__ == "__main__":
    unittest.main(verbosity=2)
