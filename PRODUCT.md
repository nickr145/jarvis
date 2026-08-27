# Jarvis — Product context

## Register
product — a dashboard the user reads while in a task, not a page that sells anything.

## Platform
web — laptop-first. Launched by typing `jarvis` in a terminal, which opens a
browser. Responsive down to phone, but the desktop read is the one being
designed for.

## Users
One person: the owner of the repo. A recent CS + business graduate job-hunting
in Toronto. Reads this once, in the morning, before deciding what to do with
the day. No second audience — there is no sharing, no multi-user state, no
account.

## Purpose
Answer one question in about thirty seconds: *is there anything I need to
handle today?* Success is not opening Gmail or a news site afterwards.

## Positioning
A briefing assembled from his own accounts, where every figure on screen comes
from a file an agent actually wrote.

## Brand personality
Instrumentation. Calm, technical, legible. A readout, not a report.

## Anti-references
- **Fabricated data of any kind.** The project exists in reaction to a staged
  "Jarvis" demo whose dashboard numbers were invented for the video. The look
  was never the problem; unsourced figures were. Every number here is derived
  from `output/*.json` at render time.
- Generic SaaS admin: purple gradients, uniform card grids, an icon beside
  every heading, a decorative hero metric.
- Neon-everything sci-fi costume. HUD language is welcome; unreadable is not.
- Consumer-app cheer — pastels, illustrations, encouraging copy. Wrong register
  for 7am.

## Strategic design principles
1. **An empty panel is a finding.** Emptiness is rendered deliberately and says
   why it is empty. It is never padded, and never disguised as loading.
2. **A failed fetch renders as a failure**, never as stale data presented as
   current.
3. **Every metric is derived, never authored.** If a number cannot be computed
   from a file on disk, it does not appear.
4. Density is fine. This is read by someone who wants the whole picture at once.

## Accessibility
WCAG AA. Body text ≥4.5:1, large text ≥3:1, verified against the dark ground.
Colour is never the only carrier of meaning — counts and labels accompany every
state colour. Full `prefers-reduced-motion` support.
