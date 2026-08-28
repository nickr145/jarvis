# Jarvis

Personal daily-brief tool. A local portal showing categorized email, news,
and a weekly LinkedIn draft. See [`docs/jarvis-design-doc.md`](docs/jarvis-design-doc.md)
for the full plan.

**One rule:** every panel renders from a file an agent actually wrote. No
placeholder data. An empty panel is honest; a fake populated one isn't.

## Status
- [x] design doc
- [x] `news_agent.py` — stdlib only, no API key, writes `news.json`
- [x] email agent — Gmail MCP + [`config/email_rules.md`](config/email_rules.md)
- [x] job-alert miner — parse listings out of digests (LinkedIn + Indeed)
- [x] portal — static page + `jarvis` launcher
- [x] ATS poller — Workday boards, `agents/ats_poll.py` (step 3c)
- [ ] use it for a week, fix what's annoying
- [ ] linkedin content agent (draft-only)
- [ ] voice

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
```
No dependencies — everything is stdlib or runs as a Claude Code subagent.
No `.env` needed; nothing here calls the metered API.

## Running
```bash
./jarvis --install       # symlink into ~/.local/bin, then `jarvis` works anywhere
jarvis                   # refresh news, rebuild listings, open the portal (~2s)
jarvis --poll            # also poll employer job boards (~70s)
jarvis --no-refresh      # open whatever is already on disk
jarvis --port 8931       # if 8731 is taken
```

`jarvis` cannot refresh email: the Gmail connector lives in a Claude Code
session, so a plain terminal can't reach it. It uses whatever `email.json` the
last Claude Code run left, and the portal shows a banner when that file is more
than a day old — an empty "Needs you" panel should never be mistaken for
"nothing arrived" when it means "nobody has looked since Tuesday".
Or run an agent on its own:
```bash
python agents/news_agent.py     # → output/YYYY-MM-DD/news.json
```
The email agent runs as a Claude Code subagent (`.claude/agents/email-agent.md`,
needs the Gmail connector authenticated via `/mcp`). It writes
`output/YYYY-MM-DD/email.json` and `listings.json`.

```bash
python3 agents/ats_poll.py         # poll employer boards → listings_ats.json
python3 agents/build_listings.py   # merge every source → listings.json
python3 tests/test_alert_parser.py && python3 tests/test_workday.py
```
