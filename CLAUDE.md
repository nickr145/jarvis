# Jarvis — working agreement

Full plan: `docs/jarvis-design-doc.md`. Read it before proposing changes.

## The honesty rule

Every panel in the portal renders from a file an agent actually wrote. No
placeholder data, no sample values, no invented numbers — not even
temporarily while building. If an agent hasn't run, its panel is empty and
says so. This project exists because a staged demo made this mistake.

The same rule applies to generated text: if a model can only restate its
input at greater length, don't generate it. That's padding shaped like
analysis.

## Shipping

Each numbered build step gets its own branch and PR. Never merge or push to
`main` directly — merging is the user's call.

**Use the `shipping-a-step` skill when a step is finished.**

## Commits

Do not append a `Co-Authored-By` trailer.
