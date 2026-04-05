---
name: align
description: Update specs in reference-docs/ to match feedback + goal. No code changes — specs only. Called by /self-improve.
allowed-tools: Read Grep Glob Bash Write Edit
effort: medium
---

# Align — Feedback → Specs

Update `reference-docs/` specs to reflect feedback and goal. Don't write code — just update specs.

## Steps

1. Read `reference-docs/goal.md`.
2. Read latest `feedback-*.md` files. Look at "Suggested Spec Changes" section.
3. Read current specs in `reference-docs/`.
4. For each suggested spec change from feedback:
   - Does it serve the goal's stated pain?
   - Is it a painkiller or a vitamin?
   - If painkiller: update the spec.
   - If vitamin: skip it.
5. Remove spec sections that don't serve the goal. Add sections for feedback items that do.
6. Output a summary of what specs changed and why.

The next `/build` cycle will implement from the updated specs.
