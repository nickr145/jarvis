# Email classification rules

Read by the email agent. Plain prose on purpose — this is the agent's actual
logic, and it should be editable without touching any wiring. If a brief
surfaces the wrong thing, the fix usually belongs in this file.

**Read-only.** Never send, reply, archive, label, mark as read, or modify any
message. Classification only.

## Scope

Unread messages in the inbox, received **since the last brief** — look at the
most recent dated directory under `output/` and use that date as the floor.
If there is no previous brief, or it is more than 7 days old, fall back to the
last 24 hours.

Anchoring to the last brief rather than a fixed 24 hours means skipping a
weekend doesn't silently drop Friday's mail.

## Categories

Exactly one per message. When two apply, the earlier rule below wins.

### 1. `job_opportunity`

**Tuned for recall — a missed opportunity costs more than a noisy panel.**

Anything plausibly about a role: recruiter outreach, application status
updates, interview scheduling, referral offers, job alerts from boards.
Include generic mass recruiter mail. When genuinely unsure whether something
is job-related, classify it here rather than as `fyi`.

This is the one category where over-surfacing is the correct error. Do not
filter for quality — that's what `priority` is for.

Takes precedence over `needs_reply`: a recruiter asking "are you interested?"
is a `job_opportunity`, not a reply obligation.

### 2. `needs_reply`

**Tuned for precision — this panel is only useful if it stays short.**

All three must hold:
- A real person wrote it (not automated, not bulk)
- It was sent to the user directly, not a list they happen to be on
- **It asks a question, makes a request, or needs a decision from them**

The third condition is what keeps the panel trustworthy. "Thanks!", "sounds
good", "received" and similar acknowledgements are `fyi`, not `needs_reply` —
they were written by a human but need nothing back.

A statement that only implies action ("I've sent over the draft") is `fyi`.
Accept that a genuinely important email phrased as a statement will be missed
here; that's the deliberate trade.

### 3. `newsletter`

Subscribed bulk mail: has an unsubscribe header or link, sent to a list, no
individual author addressing the user. Marketing, digests, product updates,
newsletters proper.

### 4. `fyi`

Everything else. Automated but not subscribed — receipts, order confirmations,
security alerts, calendar invites, CI notifications, GitHub mail. Also human
mail needing no response.

## Priority

`high` or `normal`. Most things are `normal`; `high` is for what would be
genuinely bad to see a day late.

Mark `high` when:
- A `job_opportunity` names a **specific role** and mentions the user's
  keywords — *product manager*, *AI*, *remote* — or is clearly personalized
  rather than a mass send
- A `job_opportunity` carries a deadline or an interview time
- A `needs_reply` is time-sensitive, or is a follow-up to something the user
  has already not answered

Everything else is `normal`. Bulk recruiter blasts are `job_opportunity` +
`normal` — surfaced, not shouted about.

## The `note` field

One sentence on why this message landed in this category. Not a summary of the
email — a justification of the call.

- Good: `"Names a specific PM role and mentions remote; personalized."`
- Good: `"Human sender, but only acknowledges receipt — nothing to answer."`
- Bad: `"Email from a recruiter about a job."`

This field is how the classifications get debugged in the first weeks. If a
note can't explain the call, the call was probably wrong.

## Output

`output/YYYY-MM-DD/email.json`:

```json
{
  "generated_at": "ISO-8601 with offset",
  "window_start": "ISO-8601 — the floor actually used",
  "items": [
    {
      "category": "job_opportunity | needs_reply | fyi | newsletter",
      "sender": "Display Name <address>",
      "subject": "...",
      "date": "ISO-8601 with offset",
      "priority": "high | normal",
      "note": "why it was classified this way"
    }
  ]
}
```

On failure — auth expired, API unreachable — write `items: []` plus an
`error` string. The portal renders that as a failed panel. **Never write a
partial list as though it were complete**, and never invent an entry.
