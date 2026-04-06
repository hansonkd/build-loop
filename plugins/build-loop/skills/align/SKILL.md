---
name: align
description: Update specs in reference-docs/ to match feedback + goal. No code changes — specs only. Used by /self-improve or standalone.
allowed-tools: Read Grep Glob Bash Write Edit
effort: medium
---

# Align — Feedback → Specs

Update `reference-docs/` specs to reflect feedback and goal. Don't write code — just update specs.

## Steps

1. Read this session's goal: `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md`.
2. Read this session's latest `reference-docs/sessions/${CLAUDE_SESSION_ID}/feedback-*.md`. Look at "Suggested Spec Changes" section. Also scan other sessions' feedback.
3. Read current shared specs in `reference-docs/` (not inside sessions/).
4. For each suggested spec change from feedback:
   - Does it serve the goal's stated pain?
   - Is it a painkiller or a vitamin?
   - If painkiller: update the spec.
   - If vitamin: skip it.
5. Remove spec sections that don't serve the goal. Add sections for feedback items that do.
6. Output a summary of what specs changed and why.

The next `/build` cycle will implement from the updated specs.
