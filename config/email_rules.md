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

Anything about **an application or candidacy this user already has**, plus
genuine approaches. Two families:

*Transactional* — automated but about their specific application: status
updates, assessment invitations and reminders, interview confirmations,
rejections, "we received your application". These arrive from `noreply@`
addresses and still belong here.

*Approaches* — a recruiter or hiring manager writing to them personally.

When genuinely unsure whether something is a real approach or a broadcast,
classify it here rather than as `job_alert`.

Over-surfacing is the correct error **here**. Do not filter for quality —
that's what `priority` is for.

A recruiter asking "are you interested?" is a `job_opportunity` **and** sets
`needs_response: true` — see below. Category and actionability are separate
questions.

### 2. `job_alert`

Automated digests from job boards, alert services and talent communities —
LinkedIn job alerts, Indeed alerts, Haystack, company talent-community
mailers. The content is a listing feed rather than an approach.

**The test is engagement, not sender.** Does the message concern a role the
user has already engaged with — an application ID, "your application", "your
assessment", "your interview"? That is `job_opportunity`, however automated the
sender looks. Is it presenting roles they have not engaged with? That is a
`job_alert`.

Sender address is never the test. Real cases from this inbox:

- `noreply@mail.amazon.jobs` — a no-reply address on a jobs subdomain, and it
  carries *"your application will not be considered until all sections of the
  assessment are completed"*. Highest-stakes mail in the account.
- `TD@myworkday.com` — an ATS address; a human recruiter wrote through it.
- `info@devstaff.ca` — a generic inbox address; a named recruiter wrote
  *"I came across your profile and thought you might be a great fit."*
- `yogita.chharia.venuiti.com@viazohorecruit.com` — an ATS relay carrying a
  personal message with an attached job description.

A domain-based rule misfiles every one of these.

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

For human mail that needs an answer and is **not** job-related. Job mail
needing an answer stays `job_opportunity` with `needs_response: true`, so the
jobs panel keeps its context and the reply signal is not lost.

**Tuned for precision — this panel is only useful if it stays short.**

Both must hold:
- A real person wrote it (not automated, not bulk marketing)
- **It asks a question, makes a request, or needs a decision from them**

*Removed:* an earlier version also required the mail be addressed directly
rather than to a list. Real mail broke it — Amazon's assessment invitation and
TCS's interview job description both went to `Undisclosed recipients:;`, and
both mattered. A BCC blast can still carry an interview time.

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

## `needs_response`

A boolean, set independently of category. **This is the actionability signal,
and it is what the brief's "Needs you" panel keys off.** Category says what a
message is; this says whether the user owes anything.

Set `true` when the message asks a question, requests information, proposes a
time, or otherwise cannot be left alone without something breaking.

Set `false` when it is informational: a rejection, an acknowledgement, a
receipt, a listing feed, a newsletter. Most mail is `false`.

**Thread state overrides content.** If the newest message in the thread was
sent by the user, nothing is owed — `needs_response: false`, whatever the
text says. A question already answered is not an open question.

### `awaiting_reply`

A second boolean, the mirror image. Set `true` when the newest message in the
thread is **from the user**, it asked something, and more than 5 days have
passed with no response.

This is a real state that `needs_response` cannot express. In this inbox, the
user asked a TCS recruiter *"Could you let me know a time that works?"* on
11 August and nothing came back. Nothing is owed by the user — but the thread
is dying, and a brief that only ever says "you owe replies" will never show
it. Surface these under a separate line: *waiting on them.*

Worked examples from real threads:

| Message | Category | `needs_response` |
|---|---|---|
| *"Could you please let me know a good time to connect… Tuesday between 9am and 4pm"* | `job_opportunity` | **true** — explicit request, dated |
| *"Thanks Nicholas, I have sent you a meeting request. See you then!"* | `fyi` | false — acknowledgement, nothing owed |
| *"…we've decided to move forward with other candidates"* | `job_opportunity` | false — rejection, informational |
| *"I'd like to invite you to an in-person interview"* | `job_opportunity` | **true** — needs confirmation |

## Priority

`high` or `normal`. Most things are `normal`; `high` is for what would be
genuinely bad to see a day late.

Priority tracks **urgency, not personalization.** A person-written email that
asks nothing is not high. Getting this wrong makes everything high, which
makes nothing high.

Mark `high` when:
- `needs_response` is `true` **and** there is a date, deadline, or proposed
  time attached
- A `job_opportunity` carries an interview time, an offer, or a deadline
- A `job_opportunity` names a **specific role** matching the user's
  `job_keywords` from `config/profile.json` and invites a response
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
entry, keeping the most recent. **Deduplicate within a thread as well as
across threads** — LinkedIn sent "Software Engineer I at TD" five times inside
one thread over two days, "Application Developer at CIBC" four times, and
"Python Engineer at SGA" four times. Near-identical subjects for the same role at
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
      "needs_response": true,
      "awaiting_reply": false,
      "note": "why it was classified this way"
    }
  ]
}
```

On failure — auth expired, API unreachable — write `items: []` plus an
`error` string. The portal renders that as a failed panel. **Never write a
partial list as though it were complete**, and never invent an entry.
