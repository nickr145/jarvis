"""
alert_parser.py — pull individual job listings out of board-digest emails.

A digest's subject names one role and hides the rest. One sampled LinkedIn
alert carried six jobs behind "…and more", and a two-day window held roughly
140 listings behind 23 subject lines. Reading subjects loses most of the
content, so the bodies get mined instead.

Deliberately has no Gmail dependency: it takes a plaintext body and a sender
and returns listings. The email agent fetches bodies over MCP and feeds them
here, which keeps the extraction testable against fixtures without an inbox.

**A listing that cannot be read is skipped, not guessed at.** Every field here
is lifted verbatim from the body; nothing is inferred. A block missing a title,
a company or a job id produces no listing at all.
"""

import re
from typing import Iterable

# Lines that are digest chrome rather than listing content. Order-independent.
_LINKEDIN_CHROME = re.compile(
    r"^(your job alert|new jobs match|expand your search|recommendations based"
    r"|apply with|view job:|see all jobs|view all jobs"
    r"|this email was intended|you are receiving|manage your (job alerts|recommendations)"
    r"|unsubscribe|learn why we included|help:|©)",
    re.I,
)

# Interstitial badges LinkedIn puts between the location and the link. They sit
# exactly where the location would be, so leaving them in shifts every field.
# This list is a whitelist, which means an unseen badge will corrupt a listing —
# `_looks_like_badge` is the second line of defence, and anything it catches is
# reported as unreadable rather than emitted wrong.
_LINKEDIN_BADGE = re.compile(
    r"^(fast growing|top applicant|actively recruiting|be an early applicant"
    r"|easy apply|promoted|viewed|response time|hiring in multiple locations"
    r"|\d+ (company )?alumni|\d+ connections?|school alum|alum works here"
    r"|\$[\d,]|CA\$[\d,])",
    re.I,
)

_RULE = re.compile(r"^\s*-{20,}\s*$", re.M)
_LINKEDIN_VIEW = re.compile(r"linkedin\.com/comm/jobs/view/(\d+)")

# Ranking vocabulary. Seniority is a stronger signal than any keyword match:
# a Staff or Director role is wrong for this user however well it matches.
_SENIOR = re.compile(
    r"\b(staff|principal|director|vp|vice president|head of|chief|lead|manager"
    r"|senior|sr\.?|architect|distinguished|executive)\b", re.I)
_JUNIOR = re.compile(
    r"\b(new grad|new graduate|early career|entry.level|intern|internship"
    r"|co.?op|junior|jr\.?|associate|graduate|university|student|campus)\b", re.I)
_REMOTE = re.compile(r"\bremote\b", re.I)
_SALARY = re.compile(r"[$€£]\s?\d|\bCA\$\d|\d{2,3}[kK]\s?[-–]\s?\d{2,3}[kK]")

_HOME_TOKENS = {
    "ON": (r"\bON\b", r"\bOntario\b", r"\bToronto\b", r"\bOttawa\b",
           r"\bMississauga\b", r"\bWaterloo\b", r"\bCanada\b"),
}


def _clean_linkedin_url(job_id: str) -> str:
    """Tracking parameters are ~1KB per link and carry nothing. The canonical
    view URL resolves on its own."""
    return f"https://www.linkedin.com/jobs/view/{job_id}/"


def _looks_like_badge(line: str) -> bool:
    return bool(_LINKEDIN_BADGE.match(line))


def parse_linkedin(body: str, received: str | None = None,
                   unreadable: list | None = None) -> list[dict]:
    listings: list[dict] = []
    unreadable = unreadable if unreadable is not None else []
    for block in _RULE.split(body):
        m = _LINKEDIN_VIEW.search(block)
        if not m:
            continue  # footer, "see all jobs", or anything without a real job link

        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        content = [ln for ln in lines
                   if not _LINKEDIN_CHROME.match(ln)
                   and not _LINKEDIN_BADGE.match(ln)
                   and not ln.lower().startswith("http")]
        if len(content) < 3:
            unreadable.append(m.group(1))
            continue  # cannot read title/company/location — skip rather than guess

        title, company, location = content[-3], content[-2], content[-1]
        if any(_LINKEDIN_BADGE.match(x) for x in (title, company, location)):
            unreadable.append(m.group(1))  # an unrecognised badge shifted the fields
            continue
        listings.append({
            "title": title,
            "company": company,
            "location": location,
            "url": _clean_linkedin_url(m.group(1)),
            "job_id": m.group(1),
            "source": "linkedin",
            "first_seen": received,
        })
    return listings


_PARSERS = {
    "linkedin.com": parse_linkedin,
}


def parse(body: str, sender: str, received: str | None = None) -> list[dict]:
    """Dispatch on sender domain. A source with no parser returns nothing —
    it gets counted, never guessed at."""
    return parse_report(body, sender, received)["listings"]


def parse_report(body: str, sender: str, received: str | None = None) -> dict:
    """Same as `parse`, plus what could not be read.

    The caller needs the failure count to say "12 listings, 2 unreadable"
    instead of quietly presenting 12 as the whole picture.
    """
    for domain, fn in _PARSERS.items():
        if domain in (sender or "").lower():
            unreadable: list[str] = []
            got = fn(body, received, unreadable)
            return {"listings": got, "unreadable": len(unreadable),
                    "source": domain.split(".")[0], "parser": True}
    return {"listings": [], "unreadable": 0, "source": sender, "parser": False}


def dedupe(listings: Iterable[dict]) -> list[dict]:
    """Collapse on `job_id`, keeping the earliest sighting.

    Titles are not stable — the same posting arrives worded several ways, and
    LinkedIn resent one TD listing five times inside a single thread. The
    numeric id is. Keeping the earliest `first_seen` matters because a listing
    is not new just because it was sent again.
    """
    best: dict[tuple[str, str], dict] = {}
    for it in listings:
        key = (it.get("source", ""), it.get("job_id", ""))
        prev = best.get(key)
        if prev is None:
            best[key] = it
        elif (it.get("first_seen") or "") < (prev.get("first_seen") or ""):
            best[key] = it
    return list(best.values())


def score(listing: dict, keywords: Iterable[str], home: str = "ON") -> int:
    """Location and seniority outrank keywords.

    Keyword matching alone cannot shrink this list: the user receives a
    software-engineering feed, so role keywords match roughly half of
    everything. What actually discriminates is whether the role is reachable
    (here or remote) and whether it is the right level.
    """
    title = listing.get("title") or ""
    loc = listing.get("location") or ""
    blob = f"{title} {loc}"
    s = 0

    if _SENIOR.search(title):
        s -= 8
    if _JUNIOR.search(title):
        s += 6

    patterns = _HOME_TOKENS.get(home, ())
    if any(re.search(p, loc) for p in patterns):
        s += 5
    elif _REMOTE.search(loc):
        s += 3
    elif loc:
        s -= 3  # somewhere else entirely

    if _REMOTE.search(blob):
        s += 1

    s += sum(1 for k in keywords if k and k.lower() in blob.lower())

    if _SALARY.search(blob):
        s += 1

    return s


def rank(listings: Iterable[dict], keywords: Iterable[str],
         home: str = "ON") -> list[dict]:
    """Rank, then let the caller cap. The panel is bounded by a cap rather than
    a filter, so no amount of keyword mistuning can make it unreadably long."""
    kws = list(keywords)
    scored = [(score(x, kws, home), i, x) for i, x in enumerate(listings)]
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [x for _, _, x in scored]
