# Jarvis — Personal Daily-Brief Assistant

## What this is
A personal tool (not a product) that gives me one place to start the morning:
a local portal showing my categorized email, news by category, and a weekly
LinkedIn draft — assembled by a few narrow, testable agents.

I type `jarvis` in a terminal, a portal opens in the browser, and what's
there is what the agents actually found.

## The honesty rule

The inspiration for this was a demo that turned out to be staged — a
polished Jarvis-style dashboard whose numbers were fabricated for the video.
The dashboard wasn't the problem. **Nothing was behind the panels** was the
problem.

So, one rule, and it governs every decision below:

> Every panel renders from a file an agent actually wrote. No placeholder
> data, no sample values, no lorem ipsum. If an agent hasn't run, its panel
> is empty and says so.

An empty panel looks slightly sad and is completely honest. A populated fake
one looks great and is worthless. This is the whole difference, and holding
it costs nothing except the urge to fill space while building.

Corollary: the Wealthsimple panel will be empty for a long time (see
Deferred). That panel is exactly where the original demo cheated. It stays
empty until real data can reach it.

## What "good" means
> After opening the portal, I don't feel the need to open Gmail or a news site.

If I still check both, it failed, regardless of how clean the JSON was.

## Architecture

```
agents/news_agent.py   ──→ output/YYYY-MM-DD/news.json
email agent (subagent) ──→ output/YYYY-MM-DD/email.json
                                    │
              ┌─────────────────────┴──────────────────────┐
              │                                            │
       /brief (Claude Code)                        jarvis (terminal)
       assembles markdown                          serves portal/ + output/
              │                                    opens browser
              ↓                                            ↓
   output/YYYY-MM-DD-brief.md                    localhost portal
   (readable, archived, dedupe source)           (the product)
```

Two consumers of the same JSON. The portal is what I look at; the markdown
brief is what's archived, greppable, and read back as dedupe context. Neither
is generated from the other — both read the agents' output directly.

### Runtime
Claude Code is where this is built and where the email agent runs, because
Gmail is reached through the claude.ai Gmail connector (an MCP proxy onto
`gmailmcp.googleapis.com`). That removes the entire Google OAuth setup — no
GCP project, no `credentials.json`, no refresh token on disk — at the cost of
the email agent being session-bound.

**"Standalone script first" is a news-agent rule, not a universal one.**
News is pure HTTP and behaves identically inside or outside a session, so it
earns a real script. Email cannot call an MCP server from a plain Python
process — writing it as a script first would mean building the Gmail
integration twice and throwing one away.

**But keep the logic portable.** The email classification prompt and category
rules live in `config/email_rules.md`, read by the subagent — not welded into
a subagent definition. If this ever moves to a scheduled host, the port is
"swap the Gmail transport," not "rebuild the agent."

## The portal

`portal/index.html` — one file, vanilla JS, no build step, no npm. Reads JSON
from `output/`. Served by a small Python script that starts
`http.server` and calls `webbrowser.open()`.

Chosen over FastAPI and over a React/Vite app because a static page reading
files on disk has almost nothing to break, and this project currently has no
frontend toolchain. If a live "Refresh" button is ever wanted, that's the
moment to add a real server — not before.

### Panels

| Panel | Source | Status |
|---|---|---|
| **Needs You** | `email.json` — anything with `needs_response: true` | real |
| **Waiting on them** | `email.json` — anything with `awaiting_reply: true` | real |
| **Jobs** | `email.json` — `job_opportunity`, plus top-ranked `job_alert` items | real |
| **News** | `news.json` — top 3 per category | real |
| **LinkedIn** | weekly draft, draft-only | step 6 |
| **Wealthsimple** | — | blocked, renders empty |

`fyi`, `newsletter` and `job_alert` emails collapse to a count line rather
than getting entries — except `job_alert` items matching `job_keywords`, which
are listed individually. A first run against the real inbox returned ~54
unread threads in two days, ~29 of them bulk job-board digests, so collapsing
that category is what makes the panel readable at all. Empty sections state that they're empty in one line.

### Not building: browser automation
The original demo opened Chrome and drove Gmail. Skipped deliberately — **a
panel showing the categorized emails makes opening Gmail pointless.** Browser
automation is what you build when you don't have real data access. This has
real data access. The only browser command here is opening the portal itself.

## Agents

### News Agent — `agents/news_agent.py`
- **Input:** categories from `config/profile.json`
- **Tooling:** Google News RSS (keyless, free, no account). Categories not in
  the topic map fall back to a keyword search feed, so `"artificial
  intelligence"` works as a category without any code change.
- **Budget:** top 3 items per category
- **No LLM call.** The feed carries a headline, a publisher and a link, and no
  article text. A model given only a headline and told not to invent specifics
  can only restate it at greater length — padding that reads as analysis. By
  the honesty rule, that's the same failure as a fabricated panel, smaller.
  Real summaries would require fetching and scraping the articles themselves.
- **Output** — `output/YYYY-MM-DD/news.json`:
```json
{
  "generated_at": "ISO-8601 with offset",
  "categories": [
    {"category": "world | financial | sports | tech",
     "items": [{"headline": "...", "source": "...", "source_url": "...",
                "url": "...", "published": "ISO-8601 with offset"}],
     "error": "present only on failure"}
  ]
}
```
`published` is offset-aware (the feed reports GMT) — the portal must convert
to local time, not truncate the string.

### Email Agent — subagent definition + `config/email_rules.md`
- **Input:** Gmail inbox, read-only
- **Tooling:** Gmail MCP — the claude.ai Gmail connector, OAuth'd once
- **Output (JSON):**
```json
{
  "items": [
    {
      "category": "job_opportunity | job_alert | needs_reply | fyi | newsletter",
      "sender": "...",
      "subject": "...",
      "date": "...",
      "priority": "high | normal",
      "needs_response": true,
      "awaiting_reply": false,
      "note": "why it was classified this way"
    }
  ]
}
```
- A collection, matching the news agent's shape. `date` is carried because
  "3 days old and unanswered" is what makes a needs-reply item urgent.
- Read + classify only. Never sends, archives, or labels.

### LinkedIn Content Agent — step 6
- **Input:** `config/profile.json` (topics, tone, cadence) **plus that week's
  brief files from `output/`** as source material. Topic keywords alone
  produce generic posts; drafts worth editing come from something I actually
  read this week.
- **Tooling:** Buffer MCP (`mcp.buffer.com/mcp`, first-party)
- **Output:** draft post text + suggested time — **never auto-publishes.**

## Dedupe
`/brief` reads the most recent `output/*-brief.md` and passes it in as
context, with the instruction to skip what's already covered and prefer
genuinely new developments. No state file, no id tracking. This handles
"same story, new angle" — which exact-match id dedupe always gets wrong.

## Failure behavior
Panels and sections fail independently. If Gmail auth has expired or the news
feed times out, the portal still opens with `News unavailable — feed timed
out` in that panel. A partial brief beats no brief. This is also the honesty
rule in practice: a failed fetch renders as a failure, never as stale data
presented as current.

## Configuration

`config/profile.json`:
```json
{
  "news_categories": ["world", "financial", "tech", "sports"],
  "job_keywords": ["product manager", "AI", "remote"],
  "linkedin_topics": ["AI tooling", "career growth"],
  "linkedin_cadence_days": 3
}
```
`briefing_time` drops out — scheduling is deferred, and a config field for a
feature that doesn't exist is a lie about what the tool does. It returns with
step 7. (Still present in the current file; remove it when touching it next.)

`config/email_rules.md` — the classification prompt and category definitions,
kept as prose so it's editable without touching agent wiring.

### Dependencies
`requirements.txt` is **empty**. Nothing here needs a third-party package:

- News agent — stdlib `urllib` + `ElementTree`. `feedparser` turned out to be
  unnecessary too: the feed has a real `<source>` element carrying the
  publisher name and homepage, so the fragile `" - "` split is gone.
- Email + LinkedIn agents — Claude Code subagents over MCP. No packages.
- Portal — stdlib `http.server` and `webbrowser`.
- No Google libraries. That's the MCP choice paying for itself.

**`.env` is also unnecessary.** Nothing needs `ANTHROPIC_API_KEY`: the agents
that call a model run on the Claude Code subscription, not the metered API.
(Worth knowing that those are separate — a Max plan carries no API credits,
which is what killed the original LLM-summarizing news agent.)

If a real news API is ever wanted: Currents (~600–1,000 req/day, commercial
use OK), NewsData.io (200 credits/day), GNews (~100/day, non-commercial).
This tool makes ~4 requests per day, so all three are overkill and RSS stays
the right answer.

## Deferred

- **Voice.** Genuinely wanted, genuinely last. Input via the Web Speech API
  (free, built into Chrome) so talking to it costs nothing; ElevenLabs for a
  spoken reply is a small add-on after that. Worth zero until the panels have
  something to read out.
- **Wealthsimple.** No official public read-only API. The only route is
  Truthifi's Plaid/Yodlee MCP bridge (paid tier + Claude Pro+) — real and
  viable, but its own setup project. Panel stays empty until then. **No
  manual-entry placeholder numbers.**
- **Scheduling / Railway.** Requires the Gmail OAuth path, since a cron job
  can't use a session-bound MCP. When earned: write `email_agent.py` against
  `google-api-python-client` reusing `config/email_rules.md`, then deploy.
- **Browser automation** — cut, see above.
- Auto-publishing to LinkedIn or anywhere. Gmail write/send actions.

## Build order
1. This doc — done
2. News Agent — run it, judge the summaries. Write `news.json`.
3. Email Agent as a Claude Code subagent over Gmail MCP — run against real
   inbox, judge the classifications. Write `email.json`.
4. **The portal.** Static page + `jarvis` launcher. Two real panels.
5. Use it every morning for a week. Fix what's annoying.
6. LinkedIn Content Agent (draft-only), fed by that week's briefs.
7. Voice. Then Wealthsimple or scheduling, if still wanted.

Steps 2 and 3 come before 4 on purpose: the portal is only allowed to render
data that already exists, so the agents have to be real first. That ordering
is the honesty rule expressed as a schedule.
