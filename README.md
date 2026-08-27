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
./jarvis                 # refresh news, open the portal
./jarvis --no-refresh    # open whatever is already on disk
./jarvis --port 8931     # if 8731 is taken
```
Or run an agent on its own:
```bash
python agents/news_agent.py     # → output/YYYY-MM-DD/news.json
```
The email agent runs as a Claude Code subagent (`.claude/agents/email-agent.md`,
needs the Gmail connector authenticated via `/mcp`). It writes
`output/YYYY-MM-DD/email.json` and `listings.json`.

```bash
python3 tests/test_alert_parser.py    # parser tests, stdlib only
```
