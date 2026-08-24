# Jarvis

Personal daily-brief tool. A local portal showing categorized email, news,
and a weekly LinkedIn draft. See [`docs/jarvis-design-doc.md`](docs/jarvis-design-doc.md)
for the full plan.

**One rule:** every panel renders from a file an agent actually wrote. No
placeholder data. An empty panel is honest; a fake populated one isn't.

## Status
- [x] design doc
- [ ] `news_agent.py` — written, not yet judged. Run it, read the summaries.
- [ ] email agent — Claude Code subagent over Gmail MCP
- [ ] portal — static page + `jarvis` launcher
- [ ] use it for a week, fix what's annoying
- [ ] linkedin content agent (draft-only)
- [ ] voice

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

## Running an agent standalone
```bash
python agents/news_agent.py
```
