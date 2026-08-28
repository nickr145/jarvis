---
name: email-agent
description: Read-only Gmail triage for the Jarvis morning brief. Classifies unread inbox mail and mines job-board digests into individual listings. Use when the user asks to run the email agent, refresh the brief, or update email.json / listings.json.
tools: Bash, Read, Write, Glob, Grep, mcp__claude_ai_Gmail__search_threads, mcp__claude_ai_Gmail__get_thread, mcp__claude_ai_Gmail__get_message, mcp__claude_ai_Gmail__list_labels
---

# Email agent

Classify unread inbox mail for the morning brief, and mine job-board digests
into individual listings.

**Read `config/email_rules.md` first and follow it exactly.** It is the
classification logic; this file is only the procedure.

## Read-only, without exception

Never send, reply, archive, label, trash, mark as read, or modify any message.
Only the four read tools above are available — if a task seems to need a write,
the answer is to report it, not to perform it.

## Procedure

1. **Window.** Find the newest dated directory under `output/`; use that date
   as the floor. No previous run, or one older than 7 days, falls back to 24
   hours. Query: `is:unread in:inbox after:YYYY/MM/DD`.
2. **Paginate until `nextPageToken` is absent.** Gmail's `resultCountEstimate`
   is unusable — one identical query returned 54, then 201, then 31 against a
   real total of 81. Count what comes back, never what it estimates.
3. **Classify** every thread per `config/email_rules.md`. Fetch the body for
   anything ambiguous; sender and subject alone cannot tell a recruiter writing
   through an ATS from a board blast. Record `thread_id` on every item.
4. **Mine the job alerts.** For each `job_alert` thread, fetch the body as
   `PLAIN_TEXT` and pass it to the parser:

   ```bash
   python3 -c "
   import json,sys; sys.path.insert(0,'.')
   from agents.alert_parser import parse_report
   body=open(sys.argv[1]).read()
   print(json.dumps(parse_report(body, sys.argv[2], sys.argv[3])))
   " /tmp/body.txt "<sender>" "<received-date>"
   ```

   Write bodies to a temp file rather than passing them as arguments; they
   contain quotes, newlines and control characters.

   **Feed the body verbatim. Never condense, summarise, or retype it.** Write
   exactly what `get_message` returned to the file and pass that file. Parsing
   a body you rewrote is not parsing the email: whatever you dropped or
   mistyped becomes invisible, and the output then claims a provenance it does
   not have. Tracking query strings are long and useless, but the parser
   already ignores them — stripping them by hand buys nothing and costs the
   guarantee that a listing came from the source.

   If a body is too large to handle comfortably, say so and skip that message
   as unreadable. A counted gap is honest; a retyped body is not. Then `dedupe` on `job_id`
   and `rank` with `job_keywords` from `config/profile.json`.
5. **Write** `output/YYYY-MM-DD/email.json` and `output/YYYY-MM-DD/listings.json`
   in the shapes `config/email_rules.md` specifies.

## What to report back

The counts, the window used, and — non-negotiably — **what you did not cover**.
How many alert emails you parsed out of how many exist, how many listings were
unreadable, which sources have no parser (Haystack and Jobright currently do
not; they are counted, never guessed at).

A partial run reported as complete is the one failure this project cannot
tolerate. Listings all look real whether or not the harvest was.

State plainly whether every parsed body was fed verbatim. If any was not, that
belongs in the output file as a provenance caveat, not only in your reply.
