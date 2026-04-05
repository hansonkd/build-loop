---
name: research
description: Gather external signals and write structured feedback. Called by /self-improve when no recent feedback exists.
context: fork
agent: general-purpose
allowed-tools: Read Grep Glob Bash Agent Write
effort: high
---

# Research — Gather External Signals

Launch 1-2 sonnet subagents to pull signals from available sources. Synthesize into structured feedback.

## Session isolation
Per-session state is at `reference-docs/sessions/${CLAUDE_SESSION_ID}/`. Read this session's goal from there. Write feedback there. Also scan other sessions' feedback for cross-pollination.

## Before starting: Check pace
Read `.claude/sessions/${CLAUDE_SESSION_ID}/pace-metrics.json` if it exists. If PAUSE or SLOW, skip — research is deferrable. If CONSERVE, read fewer sources (3-5 instead of 5-10).

## Sources to check (use the 3-agent pattern)
Launch up to 3 sonnet subagents in parallel, each scanning a different source type. This prevents tunnel vision and costs ~2 min wall time:

- **Signal scanner:** HN digests (look for `hackernews*` or `data/digest*` dirs in repo, read 5-10 most recent), or web search for recent discourse around the goal's pain.
- **Code/infra scanner:** GitHub issues (`gh issue list --limit 20`), recent PRs, competitor repos. What are people building in this space?
- **User/market scanner:** Any source the user specified in this session's goal or evaluation files. Community forums, Twitter threads, Reddit posts about the pain.

Not all sources will exist for every project. Skip what's not available.

## Read the goal first
Read `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md`. Every signal is evaluated against the stated pain.

## Output
Write to `reference-docs/sessions/${CLAUDE_SESSION_ID}/feedback-YYYY-MM-DD.md`:

```markdown
# Feedback — YYYY-MM-DD

## Painkiller Check
[YES/NO — is the goal's pain confirmed by external signals? One sentence.]

## Top Signals
1. **[Signal]** — [What it means for the product]
2. ...

## Suggested Spec Changes
- [file] should [change] because [signal]

## Suggested Goal Changes
[If goal seems wrong, say what. Otherwise: "Goal aligned."]

## Raw Notes
[Which sources read, date ranges, for audit trail.]
```
