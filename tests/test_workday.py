"""Tests for the Workday board adapter.

The fixture is a real response from RBC's board (Canada + permanent +
Technology), with only the `facets` block stripped — the adapter never reads it
and it is enormous. Every posting is verbatim.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.workday import parse_page, board_url, job_url  # noqa: E402
from agents.alert_parser import rank, age_days  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
TENANT = {"company": "RBC", "host": "rbc.wd3.myworkdayjobs.com",
          "org": "rbc", "site": "rbcglobal1"}


def page():
    return json.loads((FIXTURES / "workday_rbc_page.json").read_text())


class WorkdayTests(unittest.TestCase):
    def test_endpoint_shape(self):
        self.assertEqual(
            board_url(TENANT),
            "https://rbc.wd3.myworkdayjobs.com/wday/cxs/rbc/rbcglobal1/jobs")

    def test_parses_every_posting_on_the_page(self):
        self.assertEqual(len(parse_page(page(), TENANT)), 20)

    def test_requisition_id_is_the_job_id(self):
        rows = parse_page(page(), TENANT)
        row = next(x for x in rows if x["title"] == "Lead Platform Engineer")
        self.assertEqual(row["job_id"], "R-0000185627")
        self.assertEqual(row["company"], "RBC")
        self.assertEqual(row["source"], "workday:rbc")
        self.assertEqual(row["via"], "poll")

    def test_url_resolves_to_the_public_posting(self):
        row = parse_page(page(), TENANT)[0]
        self.assertTrue(row["url"].startswith(
            "https://rbc.wd3.myworkdayjobs.com/rbcglobal1/job/"))

    def test_posting_without_a_requisition_id_is_skipped_not_invented(self):
        p = page()
        p["jobPostings"][0]["bulletFields"] = []
        self.assertEqual(len(parse_page(p, TENANT)), 19)

    def test_shape_matches_the_email_miner(self):
        row = parse_page(page(), TENANT)[0]
        for key in ("title", "company", "location", "url", "job_id",
                    "source", "salary", "posted", "first_seen"):
            self.assertIn(key, row)

    def test_workday_posted_strings_are_understood_by_age_days(self):
        rows = parse_page(page(), TENANT)
        today = [x for x in rows if x["posted"] == "Posted Today"]
        self.assertTrue(today, "fixture should contain a same-day posting")
        self.assertEqual(age_days(today[0]), 0.0)
        older = next(x for x in rows if x["posted"] == "Posted 2 Days Ago")
        self.assertEqual(age_days(older), 2.0)

    def test_seniority_ranking_sinks_this_page(self):
        """The page is almost all Lead/Senior/Architect. Ranking must not put
        one of those first when a junior role is present."""
        rows = parse_page(page(), TENANT)
        junior = {"title": "Associate Software Developer", "company": "RBC",
                  "location": "TORONTO, Ontario, Canada", "posted": "Posted Today"}
        ranked = rank(rows + [junior], ["software", "developer"], home="ON")
        self.assertEqual(ranked[0]["title"], "Associate Software Developer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
