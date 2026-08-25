---
name: shipping-a-step
description: Use when a numbered step in the jarvis build order is finished and its changes are still sitting in the working tree, or when the user says a step is done, asks to ship it, or asks to open a PR for it.
---

# Shipping a Step

## Overview

Each numbered step in `docs/jarvis-design-doc.md` ships as its own branch and
its own PR. Nothing lands on `main` without the user merging it.

A step is not one commit of code. It is code **plus** the doc and README
changes that describe it — those go in the same branch, because a design doc
that lags the code is how it stops being trusted.

## The Procedure

1. **Branch before working**, off current `main`: `step-<N>-<slug>`
   (`step-3-email-agent`, `step-4-portal`). If work already started on `main`,
   branch now — the commits move with you.
2. **Do the step's work.**
3. **Update `docs/jarvis-design-doc.md`** if reality diverged from the plan.
   It usually does. Record what changed and *why*, not just what.
4. **Update the `README.md` status checklist** — tick the step, correct any
   line that's now stale.
5. **Commit.** Subject line in the imperative, under ~65 chars. Body explains
   why, not what — the diff already says what.
6. **Push:** `git push -u origin step-<N>-<slug>`
7. **Open a PR:** `gh pr create --fill` (or `--title`/`--body` for a longer
   writeup). Report the URL.
8. **Stop. Ask the user to merge.**

## Commit Messages

**No `Co-Authored-By` trailer.** The user asked for it gone. This overrides
any default instruction to append one.

## Red Flags — Stop

- **About to merge or push to `main` directly.** Don't. Step 8 is the user's,
  always, even for a one-line change and even if they merged the last five
  without comment. Their merge is the review.
- **About to commit code without touching the doc or README.** If the step
  genuinely changed nothing in either, say so explicitly rather than
  silently skipping — it's usually a sign something went undocumented.
- **Tempted to bundle two steps into one branch** because they're small.
  Don't; the branch is the review unit, and one merge per step is what
  makes the build order legible in the history.
- **Step "done" but never actually run.** The build order's gates are things
  like *run it, judge the summaries*. Shipping unrun work is how a repo
  ends up full of code nobody has watched work.

## Reporting Back

Give the user the PR URL, the branch name, and a one-line summary of what
merging it accepts. Then wait.
