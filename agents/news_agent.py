"""
news_agent.py — standalone script, no Claude Code / MCP wiring yet.

Run directly: python agents/news_agent.py
Reads config/profile.json for which categories to cover.
Should print/save structured JSON matching the shape in docs/design-doc.md.
"""

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import anthropic
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent.parent / "config" / "profile.json"

MODEL = "claude-opus-4-8"

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

SUMMARIES_SCHEMA = {
    "type": "object",
    "properties": {
        "summaries": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["summaries"],
    "additionalProperties": False,
}

_client = anthropic.Anthropic()


def load_profile() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _fetch_headlines(category: str, limit: int = 5) -> list[dict]:
    topic = GOOGLE_NEWS_TOPICS.get(category.lower())
    if topic:
        url = f"https://news.google.com/rss/headlines/section/topic/{topic}?hl=en-US&gl=US&ceid=US:en"
    else:
        url = f"https://news.google.com/rss/search?q={quote(category)}&hl=en-US&gl=US&ceid=US:en"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        root = ET.fromstring(resp.read())

    headlines = []
    for item in root.findall("./channel/item")[:limit]:
        title = item.findtext("title") or ""
        headline, _, source = title.rpartition(" - ")
        headlines.append({
            "headline": headline or title,
            "source": source or "Google News",
            "url": item.findtext("link") or "",
        })
    return headlines


def get_news_for_category(category: str) -> dict:
    headlines = _fetch_headlines(category)
    if not headlines:
        return {"category": category, "items": []}

    numbered = "\n".join(
        f"{i + 1}. {h['headline']} ({h['source']})" for i, h in enumerate(headlines)
    )
    response = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": SUMMARIES_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                f"Here are {len(headlines)} real, current news headlines in the "
                f"'{category}' category:\n\n{numbered}\n\n"
                f"Write a 1-2 sentence summary for each, in the same order, as a "
                f"JSON list of strings. Base each summary only on what its headline "
                f"tells you — do not invent specifics the headline doesn't support."
            ),
        }],
    )

    text = next(block.text for block in response.content if block.type == "text")
    summaries = json.loads(text)["summaries"]

    items = [
        {
            "headline": h["headline"],
            "summary": summary,
            "source": h["source"],
            "url": h["url"],
        }
        for h, summary in zip(headlines, summaries)
    ]
    return {
        "category": category,
        "items": items,
    }


def main():
    profile = load_profile()
    results = [get_news_for_category(c) for c in profile["news_categories"]]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()