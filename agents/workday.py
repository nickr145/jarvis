"""
workday.py — poll employers' Workday boards directly.

Job alerts are a platform-curated sample on the platform's schedule. Polling
the employer gives everything, when it posts. RBC's board carries 241 permanent
technology roles in Canada; the same window's email alerts carried two or three.

Split like the digest parser: `parse_page` is pure and takes a decoded response,
`fetch_tenant` does the network. The parsing is therefore testable against a
saved real response with no network at all.

**Workday exposes no seniority facet.** Category, Country, Employment Type and
Job Type are all it offers, so "entry level" cannot be filtered server-side — it
is inferred from titles by `alert_parser.rank`, which already sinks Senior,
Staff, Lead and Director.

One caution on the Employment Type facet: on an early-talent board every
posting is "Full time", because a co-op is full time for its fixed term. The
axis that separates permanent from co-op is `workerSubType` (`Regular` vs
`Student/Coop (Fixed Term)`).
"""

import json
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "jarvis-personal-brief/0.1 (personal job search; low volume)"

# Politeness. A daily run at this size is a fraction of what one person
# browsing the same board would issue.
PAGE_SIZE = 20
PAGE_DELAY_S = 1.5
MAX_PAGES = 15


def board_url(tenant: dict) -> str:
    return (f"https://{tenant['host']}/wday/cxs/{tenant['org']}"
            f"/{tenant['site']}/jobs")


def job_url(tenant: dict, external_path: str) -> str:
    return f"https://{tenant['host']}/{tenant['site']}{external_path}"


def parse_page(payload: dict, tenant: dict, received: str | None = None) -> list[dict]:
    """Turn one decoded response into listings in the miner's shape.

    A posting without a requisition id is skipped: without a stable id it
    cannot be deduplicated, and inventing one would make the same role appear
    twice on different days.
    """
    out = []
    for p in payload.get("jobPostings") or []:
        bullets = p.get("bulletFields") or []
        job_id = bullets[0] if bullets else None
        path = p.get("externalPath")
        if not job_id or not path:
            continue
        out.append({
            "title": (p.get("title") or "").strip(),
            "company": tenant["company"],
            "location": (p.get("locationsText") or "").strip(),
            "url": job_url(tenant, path),
            "job_id": job_id,
            "source": f"workday:{tenant['org']}",
            "salary": None,          # Workday's search API does not expose it
            "posted": p.get("postedOn"),
            "first_seen": received,
            "via": "poll",
        })
    return out


def _post(url: str, body: dict, timeout: int = 25) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_tenant(tenant: dict, received: str | None = None) -> dict:
    """Page through one board.

    Stops on the first failure rather than retrying into a wall, and reports the
    error instead of returning a short list that looks complete. A partial poll
    presented as a full one is the failure this project exists to avoid.
    """
    url = board_url(tenant)
    facets = tenant.get("facets") or {}
    listings: list[dict] = []
    total = None
    pages = 0

    try:
        while pages < MAX_PAGES:
            payload = _post(url, {
                "appliedFacets": facets,
                "limit": PAGE_SIZE,
                "offset": pages * PAGE_SIZE,
                "searchText": tenant.get("search_text", ""),
            })
            if total is None:
                total = payload.get("total")
            got = parse_page(payload, tenant, received)
            listings += got
            pages += 1
            if not got or (total is not None and len(listings) >= total):
                break
            time.sleep(PAGE_DELAY_S)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return {"company": tenant["company"], "listings": listings,
                "total": total, "pages": pages, "error": str(e),
                "complete": False}

    complete = total is not None and len(listings) >= total
    return {"company": tenant["company"], "listings": listings, "total": total,
            "pages": pages, "error": None, "complete": complete,
            "truncated_at_max_pages": pages >= MAX_PAGES and not complete}


def load_tenants(path: str) -> list[dict]:
    with open(path) as f:
        return [t for t in json.load(f)["tenants"] if t.get("enabled", True)]
