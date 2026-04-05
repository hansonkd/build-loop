---
name: build
description: Implement the highest-impact spec-code gap. Spec first, code second, verify third. One change per cycle. Called by /self-improve.
allowed-tools: Read Grep Glob Bash Agent Write Edit
effort: high
---

# Build — One Change, Done Properly

Pick the single highest-impact gap between specs and code. Update spec, implement, verify, commit. No half-implementations — if you can't finish it in one cycle, scope it smaller.

## Before starting: Check pace

Read `.build-loop/sessions/${CLAUDE_SESSION_ID}/pace-metrics.json` if it exists. If pace is PAUSE, skip. If SLOW, only fix BROKEN items. If CONSERVE, use sonnet subagents instead of opus.

## Steps

1. **Read state.** `reference-docs/goal.md` for the pain. All specs in `reference-docs/`. Latest `feedback-*.md` for priorities. The backlog from `.claude/loop-log.md`.

2. **Pick ONE change.** The highest-impact spec-code gap that serves the goal. Use the priority framework: BROKEN > MISSING > DEPTH > POLISH.

3. **Painkiller check.** Will a user notice this? Can you name the pain it eliminates in one sentence? If not, pick something else. Don't build infrastructure nobody sees unless it's blocking something they will see.

4. **Spec first.** Update `reference-docs/` to describe the change before writing code. If you can't describe it clearly in the spec, you don't understand it well enough to build it.

5. **Implement.** Write code matching the spec. If the code reveals the spec was wrong, update the spec first, then fix the code. Don't let them drift.

6. **Security check (build-time, not after).** Before committing, ask: Does any new code take user input? If yes: does that input go through validation/sanitization before reaching a shell, database query, or file path? Catch this now, not in a future review cycle. This turns reactive security catches into a build-time checklist.

7. **Verify.** Run tests if they exist. Verify the app starts. If there's a deploy step, run a smoke test. If anything broke, fix it before committing — don't leave broken state for the next cycle.

8. **Commit.** Message explains: what pain this addresses, what changed, what was verified. One change, one commit.

## What "done properly" means

- Tests pass (or there are no tests — but if you added behavior, add a test)
- App starts
- Spec matches code
- No partial implementations ("I'll finish this next cycle" = no)
- The change is independently useful — if the loop stops, this commit stands on its own
