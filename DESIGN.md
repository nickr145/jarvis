# Jarvis — Design system

## Theme
Dark. Chosen from the scene: read at a desk in the early morning, often before
the lights are on, on a laptop. A bright surface at that hour is hostile.

Register is instrumentation — a HUD, deliberately restrained. Cyan is a state
colour, not a wash.

## Colour

OKLCH throughout. Restrained strategy: tinted neutrals plus one accent.

| Token | Value | Role |
|---|---|---|
| `--ground` | `oklch(0.17 0.014 240)` | Page background |
| `--surface` | `oklch(0.21 0.016 240)` | Panels |
| `--surface-2` | `oklch(0.25 0.018 240)` | Rows, insets |
| `--line` | `oklch(0.32 0.020 240)` | Hairlines |
| `--ink` | `oklch(0.96 0.004 240)` | Primary text |
| `--ink-dim` | `oklch(0.74 0.012 240)` | Secondary text — 4.5:1 on ground |
| `--ink-faint` | `oklch(0.60 0.012 240)` | Labels only, never body |
| `--accent` | `oklch(0.80 0.115 205)` | Cyan. State, current, instrument rules |
| `--alert` | `oklch(0.82 0.135 75)` | Amber. Needs a response |
| `--dead` | `oklch(0.55 0.020 240)` | Blocked / not built |

Neutrals are tinted 0.014–0.020 chroma toward the accent's hue, not toward
generic warmth.

## Typography

Two families on a genuine contrast axis — humanist sans for prose, monospace
for anything that is data.

- **UI / prose**: `ui-sans-serif, -apple-system, "Segoe UI", Inter, sans-serif`
- **Data / readouts**: `ui-monospace, "SF Mono", "JetBrains Mono", monospace`

Fixed rem scale, ratio ~1.2 — product UI, not fluid brand type. No display
faces in labels or data.

## Layout
Single column, max 1100px. Panels stack; the readout strip spans full width.
Responsive behaviour is structural — the strip wraps, panel rows reflow. Type
does not scale fluidly.

## Motion
150–250ms, ease-out. Motion conveys state only: row hover, panel focus, the
readout counting up once on load. Content is visible by default and never
gated behind a transition. Full reduced-motion alternative.

## Components
Panels have four states, all designed: **populated**, **empty** (with the
reason), **failed** (with the error), **not built**. The last two are visually
distinct from empty — a blocked panel must not look like a quiet morning.
