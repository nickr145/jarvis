# Jarvis without Claude Code — migration scope

**Status: not started.** This is a design doc for a possible future track, not
a build step. Nothing here changes until the current work (`docs/jarvis-design-doc.md`,
currently step 5) is done. No branch, no code, no dependency added because of
this file.

## Why this exists

The current build deliberately runs the email side as a Claude Code subagent
over the claude.ai Gmail MCP connector (`docs/jarvis-design-doc.md`'s
"Runtime" section). That was the right call to get real data flowing without
a GCP project — but it means `email.json` can only ever be produced inside a
Claude Code conversation. `jarvis` (the terminal command) can serve the
portal and re-run news/ATS on its own; it can never refresh email on its own.
That's the concrete limitation, not a philosophical one: no cron job, no
"just run `jarvis --poll-email`" — someone has to come ask Claude.

The design doc's own "Deferred → Scheduling / Railway" section already named
the fix: *"Requires the Gmail OAuth path... write `email_agent.py` against
`google-api-python-client` reusing `config/email_rules.md`, then deploy."*
This doc scopes that, plus the further step of removing the LLM-in-a-session
dependency entirely (local model via Ollama), plus voice — i.e. the full
"is this possible without being a Claude Code wrapper" question.

**The honesty rule still applies in full.** Nothing here is exempt: a local
model's classification is a real classification an agent made, or the panel
is empty and says so — same as today.

## What's already portable (no work needed)

Most of the pipeline has zero Claude Code coupling today:

| Piece | Coupling |
|---|---|
| `agents/news_agent.py` | None — pure stdlib, runs anywhere |
| `agents/alert_parser.py` | None — pure function, takes a body string in |
| `agents/workday.py` / `ats_poll.py` | None — pure HTTP, stdlib |
| `agents/build_listings.py` | None — reads JSON, writes JSON |
| `portal/` + `jarvis` launcher | None — static files + `http.server` |
| `config/email_rules.md` | Portable by design — prose, not code, read by whatever classifies |

**The only two Claude-Code-bound pieces are: pulling mail, and classifying
it.** Everything downstream of `email.json` and `listings_email.json` already
doesn't care where those files came from.

## What has to change

### 1. Pulling mail — MCP connector → IMAP + App Password

Replace the Gmail MCP calls (`search_threads`, `get_thread`, `get_message`)
with `imaplib` against `imap.gmail.com:993`, authenticated with a Google App
Password (requires 2-Step Verification on the account).

- New file: `agents/email_pull.py` — network + parsing, mirrors the split
  already used in `workday.py` (pure parse function, separate fetch function)
  so it's testable against saved raw messages with no network.
- Output: raw thread/message data (sender, subject, date, body, headers) —
  **no classification**. This step only replaces *access*, not judgment.
- Credential: `GMAIL_APP_PASSWORD` in `.env` (already gitignored). Never in
  any committed config file.
- Open question, not decided here: IMAP+App Password (simple, no GCP
  project, but Google could restrict App Passwords for scripted access in
  the future) vs. the Gmail API with real OAuth (heavier setup — GCP
  project, `credentials.json`, refresh-token handling — but the durable,
  intended-for-this path, and what the design doc's Deferred section already
  named). **Recommendation when this is picked up: start with IMAP since it's
  reversible and cheap to try; move to OAuth only if IMAP proves unreliable
  or gets restricted.**

### 2. Classifying mail — Claude reasoning → local model via Ollama

This is the hard part and the actual risk in this migration. Today,
classification is me reading each thread against `config/email_rules.md` and
making judgment calls that were iterated on hard: cross-thread resolution
(the TCS phone-call case), personalization vs. urgency, sender-domain
false-negatives, "Undisclosed recipients" still being addressed to the user.
A regex classifier cannot do this. An 8B local model might not either.

- New file: `agents/classify.py` — for each pulled thread, prompts a local
  Ollama model with `config/email_rules.md` verbatim as the rulebook plus
  the thread content, asks for the same JSON shape the subagent produces
  today, writes `email.json`.
- **Gate before this replaces anything real:** run it against the existing
  test fixtures (`tests/fixtures/*`, plus the real TD/Amazon/TCS/Venuiti
  threads already used to harden the rules) and diff its output against the
  known-correct classifications already validated in this project. If it
  gets the TCS phone-call case, the category-precedence case, or the
  sender-domain case wrong, it's not ready — those are exactly the bugs that
  were already found and fixed once in the current system, and it would be
  the same failure with a different runtime.
- Fallback worth naming: keep calling the *Claude API* (metered, not the
  Code subscription) instead of Ollama for this one step, if local-model
  quality doesn't clear the bar. That's still "not a Claude Code wrapper" —
  it removes the session/UI dependency even if the model vendor is unchanged.

### 3. Feeding the miner

`agents/alert_parser.py` already takes a body string and returns listings —
it has no opinion on where the body came from. `agents/email_pull.py`'s raw
bodies feed it directly. The anti-transcription rule that's already in
`.claude/agents/email-agent.md` ("feed the body verbatim, never retype it")
becomes trivially true here, since there's no retyping step at all — the
body never passes through a model before parsing.

### 4. Orchestration — from "ask Claude" to a real script

Once 1–3 exist, `jarvis` (or a new top-level script) can run the entire
pipeline — news, mail pull, classify, ATS poll, merge/rank — with no Claude
Code session open at all. This is what actually unlocks the design doc's
deferred "Scheduling / Railway" item: a cron job or a Railway deploy can run
this, because nothing in it is session-bound anymore.

### 5. Voice (separate, already-deferred step 7 — noted here for completeness)

Not part of the email migration, but part of the same "no wrapper" question
the user asked. Stays deferred until the panels are trusted:

- Input: Web Speech API in the portal itself (free, built into Chrome) —
  no separate STT model needed unless full offline is wanted, in which case
  `whisper.cpp` runs locally.
- Output: macOS `say`, or a local TTS model, or ElevenLabs if quality matters
  enough to justify the cost.
- Command routing ("hey jarvis, any new jobs from RBC") is just string
  matching against the existing panels/agents — no new intelligence needed
  beyond what already exists.

## What does *not* change

The portal, its JSON contracts, `config/profile.json` / `config/ats_sources.json`,
the dedupe/collapse/ranking logic, the coverage/provenance fields, and the
honesty rule itself. This migration only swaps the transport and the
classifier underneath `email.json` — the shape of every output file stays
identical, so the portal doesn't need to know the migration happened.

## Suggested phase order, when this is picked up

1. **Ollama eval, standalone, before touching the pipeline.** Feed it
   `config/email_rules.md` plus the existing hardened test fixtures and see
   whether it reproduces the known-correct classifications. This is a
   go/no-go gate, not a formality — if it fails here, stop and reconsider
   (keep IMAP + Claude API instead of IMAP + Ollama).
2. `agents/email_pull.py` (IMAP), tested against a saved raw inbox dump,
   compared for thread/message-count parity against what the MCP subagent
   pulls for the same window.
3. `agents/classify.py` (whichever model won step 1), run in parallel with
   the existing subagent for a week, diffed against it daily — cut over only
   once they agree.
4. Re-point `alert_parser.py`'s input from subagent-fed bodies to
   `email_pull.py`'s raw bodies. Re-run the existing test suite unchanged —
   it's fixture-based and doesn't care about the source.
5. Fold everything into one script `jarvis` can call with no session open.
   Only now does scheduling (cron / Railway) become honestly claimable.
6. Voice, as its own project, once 1–5 are trusted daily.

Each of these, when actually started, gets its own branch and PR per the
normal shipping workflow — this doc is scope, not a step.
