# Jarvis — Personal Daily-Brief Assistant

## What this is
A personal tool (not a product, yet) that assembles a daily brief for me each
morning — news, email/job triage, and a LinkedIn content queue — by running a
few narrow, testable subagents and stitching their output together. Built for
me, used by me, no clap-trigger/voice/dashboard until the core loop works.

## What "good" means
One sentence, so there's something to judge against:

> After reading the brief, I don't feel the need to open Gmail or a news site.

If I still check both, the brief failed, regardless of how clean the JSON was.

## Runtime
Claude Code is the runtime. Gmail is reached through the claude.ai Gmail
connector (an MCP proxy onto `gmailmcp.googleapis.com`), which lives in the
Claude Code session — so the brief assembles where that session is, not on a
server somewhere. This is a deliberate
trade: it removes the entire Google OAuth setup (no GCP project, no
`credentials.json`, no refresh token on disk) at the cost of not being
schedulable until an OAuth path exists. See "Deferred" below.

**"Standalone script first" is a news-agent rule, not a universal one.**
News is pure HTTP and behaves identically inside or outside a session, so it
earns a real script. Email cannot call an MCP server from a plain Python
process — writing it as a script first would mean building the Gmail
integration twice and throwing one away.

## Architecture

```
/brief
 ├─ reads output/*.md, most recent → "already covered" context
 ├─ news-agent  (subagent) → runs news_agent.py → JSON per category
 ├─ email-agent (subagent) → Gmail MCP, read-only → JSON list
 └─ Claude assembles → output/YYYY-MM-DD-brief.md
```

There is no `orchestrator.py`. The orchestrator is the `/brief` command
itself: a prompt plus two subagent definitions. Each subagent returns
**structured data, not prose** — formatting is the orchestrator's job, and
keeping that boundary is what lets either agent be judged on its own.

## Subagents

### 1. News Agent — `agents/news_agent.py`
- **Input:** categories from `config/profile.json`
- **Tooling:** Google News RSS (keyless, free, no account)
- **Budget:** top 3 items per category
- **Output (JSON):**
```json
{
  "category": "world | financial | sports | tech",
  "items": [
    {"headline": "...", "summary": "1-2 sentences", "source": "...", "url": "..."}
  ]
}
```

### 2. Email Agent — subagent definition, no script
- **Input:** Gmail inbox, read-only
- **Tooling:** Gmail MCP — the claude.ai Gmail connector, OAuth'd once
- **Output (JSON):**
```json
{
  "items": [
    {
      "category": "job_opportunity | needs_reply | fyi | newsletter",
      "sender": "...",
      "subject": "...",
      "date": "...",
      "priority": "high | normal",
      "note": "why it was classified this way"
    }
  ]
}
```
- A collection, matching the news agent's shape. `date` is carried because
  "3 days old and unanswered" is what makes a needs-reply item urgent.
- Priority focus: surfacing job-related emails, not full inbox triage.
- Read + classify only. Never sends, archives, or labels.

### 3. LinkedIn Content Agent — deferred to step 6
- **Input:** `config/profile.json` (topics, tone, cadence) **plus that week's
  brief files from `output/`** as source material. Topic keywords alone
  produce generic posts; the drafts worth editing come from something I
  actually read this week.
- **Tooling:** Buffer MCP (`mcp.buffer.com/mcp`, first-party)
- **Output:** draft post text + suggested time — **never auto-publishes**.
  I approve/edit before it goes to Buffer's queue.

## The brief

Budgets exist so it stays readable. Top 3 news items per category. Only
`job_opportunity` and `needs_reply` emails get full entries; `fyi` and
`newsletter` collapse to a count. Empty sections say so in one line rather
than being padded.

```markdown
# Brief — Monday, Aug 24

## Needs you
- **[job]** Recruiter, Acme — "PM, AI Platform" — matches "product manager", "AI"
- **[reply]** Sarah K. — "Re: contract" — 3 days, unanswered
_+11 fyi, 4 newsletters_

## World
- **Headline** — one-line summary. [source](url)
```

### Dedupe
`/brief` reads the most recent file in `output/` and passes it in as
context, with the instruction to skip what's already covered and prefer
genuinely new developments. No state file, no id tracking. This handles
"same story, new angle" — which exact-match id dedupe always gets wrong —
and it costs nothing to build.

### Failure behavior
Sections fail independently. If Gmail auth has expired or the news feed
times out, the brief still renders with `_News unavailable — feed timed
out_` in place of that section. A partial brief at 07:30 beats no brief.

## Configuration

`config/profile.json` — how I like things:
```json
{
  "news_categories": ["world", "financial", "tech", "sports"],
  "job_keywords": ["product manager", "AI", "remote"],
  "linkedin_topics": ["AI tooling", "career growth"],
  "linkedin_cadence_days": 3
}
```
`briefing_time` drops out — scheduling is deferred, and a config field for a
feature that doesn't exist is a lie about what the tool does. It comes back
with step 7. (Still present in the current `profile.json`; remove it when
touching that file next.)

### Dependencies
`requirements.txt`:
```
python-dotenv
anthropic>=0.117,<1.0
feedparser
```
- `anthropic` is **pinned below 1.0**. A 1.x exists with breaking changes
  (httpx2, removed parameters); unpinned, the next `pip install -U` silently
  breaks the news agent.
- `feedparser` replaces hand-rolled `ElementTree` parsing. The current
  `title.rpartition(" - ")` trick to split headline from source mangles any
  headline containing " - ".
- No Google libraries. That's the MCP choice paying for itself.

`.env`:
```
ANTHROPIC_API_KEY=
```
That's the whole file. `GMAIL_CREDENTIALS_PATH` is unnecessary under the MCP
path, and `NEWS_API_KEY` is unnecessary because Google News RSS is keyless.

For reference if a real news API is ever wanted: Currents (~600–1,000
req/day, commercial use OK), NewsData.io (200 credits/day), GNews (~100/day,
non-commercial). This tool makes about 4 requests per day, so all three are
overkill and RSS stays the right answer.

## Explicitly deferred (not in this build)
- **Scheduling / Railway.** Requires the Gmail OAuth path — a cron job can't
  use a session-bound MCP. When it's earned: build `email_agent.py` against
  `google-api-python-client`, then deploy. Not before.
- **Wealthsimple** — possible via Truthifi (third-party read-only MCP bridge
  using Plaid/Yodlee, requires Truthifi paid tier + Claude Pro+). Real and
  viable, but its own small setup project (account creation, Plaid/2FA
  linking, evaluating output quality) — phase 2, not week 1.
- RevenueCat (not relevant — no app to monetize)
- Auto-publishing to LinkedIn or any platform without my approval
- Gmail write/send actions — read + classify only
- Jarvis dashboard UI
- Voice mode + ElevenLabs

These aren't cut — just sequenced after the ingestion agents are proven to
produce output I'd actually trust and use.

## Build order
1. This doc (done)
2. News Agent as a standalone Python script — run it, judge the summaries
3. Email Agent as a Claude Code subagent over Gmail MCP — run against real inbox
4. `/brief` slash command — fan out to both, assemble the markdown
5. Read it every morning for a week. Fix what's annoying.
6. LinkedIn Content Agent (draft-only), fed by that week's briefs
7. Polish: OAuth path, Railway scheduling, voice, dashboard — only if 1-6
   feel solid
