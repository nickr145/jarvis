# Jarvis — Personal Daily-Brief Assistant

## What this is
A personal tool (not a product, yet) that assembles a daily brief for me each
morning — news, email/job triage, and a LinkedIn content queue — by running a
few narrow, testable subagents and stitching their output together. Built for
me, used by me, no clap-trigger/voice/dashboard until the core loop works.

## Subagents

Each subagent is a standalone script first, wrapped as a Claude Code
subagent later. Each one returns **structured data**, not prose — the
orchestrator formats the final brief.

### 1. News Agent
- **Input:** list of source sites/RSS feeds per category
- **Tooling:** web search / fetch (or a news MCP if one fits)
- **Output (JSON):**
```json
{
  "category": "world | financial | sports | tech",
  "items": [
    {"headline": "...", "summary": "1-2 sentences", "source": "...", "url": "..."}
  ]
}
```

### 2. Email Agent (Gmail)
- **Input:** Gmail inbox, read-only
- **Tooling:** gmailMCP
- **Output (JSON):**
```json
{
  "category": "job_opportunity | needs_reply | fyi | newsletter",
  "sender": "...",
  "subject": "...",
  "priority": "high | normal",
  "note": "why it was classified this way"
}
```
- Priority focus: surfacing job-related emails, not full inbox triage.

### 3. LinkedIn Content Agent
- **Input:** personalization file (topics I post about, tone, cadence)
- **Tooling:** bufferMCP (LinkedIn only for now)
- **Output:** draft post text + suggested time — **never auto-publishes**.
  I approve/edit before it goes to Buffer's queue.

### 4. Orchestrator (Daily Brief)
- Calls News + Email (+ LinkedIn draft if one is due) agents
- Assembles one combined brief in a fixed format
- Delivery: plain text/markdown to start. Voice/dashboard come later.

## Personalization file
A single file the agents read for "how I like things," e.g. `profile.json`:
```json
{
  "news_categories": ["world", "financial", "tech", "sports"],
  "job_keywords": ["product manager", "AI", "remote"],
  "linkedin_topics": ["AI tooling", "career growth"],
  "linkedin_cadence_days": 3,
  "briefing_time": "07:30"
}
```

## Explicitly deferred (not in this build)
- Wealthsimple integration — turns out this *is* possible via Truthifi
  (third-party read-only MCP bridge using Plaid/Yodlee, requires Truthifi
  paid tier + Claude Pro+). Real and viable, but its own small setup project
  (account creation, Plaid/2FA linking, evaluating output quality) — treat
  it as a phase-2 addition once the core loop works, not a week-1 item.
- RevenueCat (not relevant — no app to monetize)
- Auto-publishing to LinkedIn or any platform without my approval
- Gmail write/send actions — read + classify only
- Jarvis dashboard UI
- Voice mode + ElevenLabs
- Automated routine/scheduling trigger

These aren't cut — just sequenced after the ingestion agents are proven to
produce output I'd actually trust and use.

## Build order
1. This doc (done)
2. News Agent as a standalone Python script — run it, judge the summaries
3. Email Agent as a standalone Python script — run against real inbox
4. Wrap both as Claude Code subagents + orchestrator
5. Daily brief delivery format (still just text/markdown)
6. LinkedIn Content Agent (draft-only)
7. Polish: routine automation, voice, dashboard — only if 1-6 feel solid
