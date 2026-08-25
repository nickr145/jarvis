"""
news_agent.py — standalone script, no Claude Code / MCP wiring needed.

Run directly: python agents/news_agent.py
Reads config/profile.json for which categories to cover.
Writes output/YYYY-MM-DD/news.json for the portal to render.

No LLM call. Google News RSS gives a headline, a publisher and a link, and
nothing else — there is no article text in the feed to condense. Asking a
model to "summarize" a headline it was handed on its own can only restate
it at greater length, so this agent reports the feed as-is.
"""

import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "profile.json"
OUTPUT_DIR = ROOT / "output"

ITEMS_PER_CATEGORY = 3

# Google News topic feeds are free, keyless, and cover most everyday categories.
# Anything not listed here falls back to a keyword search feed instead.
GOOGLE_NEWS_TOPICS = {
    "world": "WORLD",
    "financial": "BUSINESS",
    "business": "BUSINESS",
    "tech": "TECHNOLOGY",
    "technology": "TECHNOLOGY",
    "sports": "SPORTS",
}


def load_profile() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _feed_url(category: str) -> str:
    topic = GOOGLE_NEWS_TOPICS.get(category.lower())
    if topic:
        return (
            f"https://news.google.com/rss/headlines/section/topic/{topic}"
            f"?hl=en-US&gl=US&ceid=US:en"
        )
    return f"https://news.google.com/rss/search?q={quote(category)}&hl=en-US&gl=US&ceid=US:en"


def _parse_item(item: ET.Element) -> dict:
    title = item.findtext("title") or ""
    source_el = item.find("source")
    source = (source_el.text if source_el is not None else None) or "Google News"

    # Titles arrive as "Headline - Publisher"; the <source> element gives the
    # publisher separately, so strip it rather than splitting on " - " (which
    # mangles any headline that legitimately contains a dash).
    headline = title.removesuffix(f" - {source}").strip() or title

    published = item.findtext("pubDate") or ""
    if published:
        try:
            published = parsedate_to_datetime(published).isoformat()
        except (TypeError, ValueError):
            pass  # keep the raw string; better than dropping it

    return {
        "headline": headline,
        "source": source,
        "source_url": source_el.get("url") if source_el is not None else None,
        "url": item.findtext("link") or "",
        "published": published,
    }


def get_news_for_category(category: str, limit: int = ITEMS_PER_CATEGORY) -> dict:
    """Fetch one category. On failure, return an empty item list plus an
    `error` string — the portal renders that as a failed panel rather than
    letting one dead feed take down the whole brief."""
    req = urllib.request.Request(
        _feed_url(category), headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
    except (urllib.error.URLError, ET.ParseError, TimeoutError) as e:
        return {"category": category, "items": [], "error": str(e)}

    items = [_parse_item(i) for i in root.findall("./channel/item")[:limit]]
    return {"category": category, "items": items}


def main() -> None:
    profile = load_profile()
    results = [get_news_for_category(c) for c in profile["news_categories"]]

    payload = {"generated_at": datetime.now().astimezone().isoformat(), "categories": results}

    out_dir = OUTPUT_DIR / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "news.json"
    out_path.write_text(json.dumps(payload, indent=2))

    total = sum(len(r["items"]) for r in results)
    failed = [r["category"] for r in results if r.get("error")]
    print(f"{total} items across {len(results)} categories -> {out_path.relative_to(ROOT)}")
    if failed:
        print(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
