# Jarvis

Personal daily-brief tool. See `docs/design-doc.md` for the full plan.

## Status
- [ ] news_agent.py — standalone script, run it, judge summaries
- [ ] email_agent.py — standalone script, run against real inbox
- [ ] wrap both as Claude Code subagents
- [ ] orchestrator / daily brief assembly
- [ ] linkedin content agent (draft-only)
- [ ] polish: automation, voice, dashboard

## Setup
\`\`\`bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in real values
\`\`\`

## Running an agent standalone
\`\`\`bash
python agents/news_agent.py
\`\`\`