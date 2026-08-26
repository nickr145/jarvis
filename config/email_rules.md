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

Someone contacting *this user specifically* about a role: recruiter or hiring
manager outreach, application status updates, interview scheduling, offers,
referral offers, rejections. When genuinely unsure whether a message is a real
approach or a broadcast, classify it here rather than as `job_alert`.

Over-surfacing is the correct error **here**. Do not filter for quality —
that's what `priority` is for.

Takes precedence over `needs_reply`: a recruiter asking "are you interested?"
is a `job_opportunity`, not a reply obligation.

### 2. `job_alert`

Automated digests from job boards, alert services and talent communities —
LinkedIn job alerts, Indeed alerts, Haystack, company talent-community
mailers. Sender is a no-reply address belonging to a job platform; the
content is a listing feed rather than an approach.

**These are a subscription, not an opportunity.** The user signed up for them,
they arrive constantly, and against a real inbox they outnumber everything
else roughly two to one. They collapse to a count line in the brief the same
way newsletters do.

Keyword matches inside this category still surface individually — see
Priority. That's what preserves recall without flooding the panel.

Gray area, decided: `match.indeed.com` mail that opens *"Hi Nicholas, your
background could be a great match for this Strategy Analyst role"* is a
`job_alert`, not a `job_opportunity`. It is personalized by template, not by
a person. If it matches keywords it will surface on priority anyway.

### 3. `needs_reply`

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

### 4. `newsletter`

Subscribed bulk mail: has an unsubscribe header or link, sent to a list, no
individual author addressing the user. Marketing, digests, product updates,
newsletters proper.

### 5. `fyi`

Everything else. Automated but not subscribed — receipts, order confirmations,
security alerts, calendar invites, CI notifications, GitHub mail. Also human
mail needing no response.

## Priority

`high` or `normal`. Most things are `normal`; `high` is for what would be
genuinely bad to see a day late.

Mark `high` when:
- A `job_opportunity` names a **specific role** matching the user's
  `job_keywords` from `config/profile.json`, or is clearly written by a person
  rather than generated
- A `job_opportunity` carries a deadline or an interview time
- A `job_alert` names a role matching `job_keywords`. **A high-priority
  `job_alert` is listed individually in the brief rather than collapsed into
  the count** — this is the mechanism that keeps recall without flooding.
- A `needs_reply` is time-sensitive, or follows up on something the user has
  already not answered

Everything else is `normal`.

## Deduplication

Job boards resend the same listing repeatedly. In one two-day sample:
Scotiabank's talent community sent an identical notification 4×, LinkedIn sent
"Data Engineer at BMO" 3× and "Software Developer at Fidelity Canada" 2×.

Collapse messages sharing a sender and a subject within the window to a single
entry, keeping the most recent. Near-identical subjects for the same role at
the same company count as duplicates too. Note the repeat count in `note` when
it's above one.

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
      "category": "job_opportunity | job_alert | needs_reply | fyi | newsletter",
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
