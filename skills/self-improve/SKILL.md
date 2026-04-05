---
name: self-improve
description: Autonomous product development router. Checks budget, reads state, picks the single best action, delegates to a specialized skill. Use with /loop.
argument-hint: [budget-percent] [goal-summary]
allowed-tools: Read Grep Glob Bash Write Edit
effort: medium
---

# Self-Improve — Development Loop Router

You are a lightweight decision-maker. Each cycle: check budget, read state, pick ONE action, invoke the right skill. You don't do the work — you delegate. One feature per cycle, done properly. No half-implementations.

## First run: setup

If `$ARGUMENTS` has 2+ parts, parse as `<budget%> <goal-summary>`.

Write `reference-docs/goal.md` with the summary as the Pain field (see /refine-goal for format).
Write a starter `reference-docs/evaluation.md` (see /refine-evaluation for format).
Initialize `.claude/loop-log.md` with cycle 0.

If `reference-docs/goal.md` doesn't exist and no args: say "Run `/refine-goal` first" and stop.

## Each cycle

### 1. Check budget (~10 seconds)

**Requires:** `claude-rate-monitor` and `ccusage` npm packages (declared in package.json). If not installed, run `npm install` first. If commands fail, skip budget checking and run at NORMAL pace with a warning.

Run: `npx claude-rate-monitor --json`

Parse `session.utilization` (5h) and `weekly.utilization` (7d). Read budget from `reference-docs/goal.md`.

- If 5h utilization > 0.8: **PAUSE**. Log and stop.
- If 5h utilization > (budget/100) × 1.5: **SLOW**. Only /evaluate is allowed.
- If weekly utilization > 0.85 with > 2 days remaining: **SLOW** for the week.
- Otherwise: **NORMAL**.

Append one line to `.claude/pace-metrics.json` with timestamp, utilizations, pace.

**Infer other sessions:** If total utilization is rising faster than this session's contribution, other sessions exist. Adjust: `effective_budget = budget / max(1, inferred_sessions)`. Be conservative — slow down rather than starve others.

### 2. Read state (~5 seconds)

- Read `.claude/loop-log.md` — what did last cycle do? What's in the backlog?
- `git log --oneline -5` — recent work
- Check for `reference-docs/feedback-*.md` — any feedback?
- Count: cycles since last evaluation, last simplification, last structural work
- Quick check: do tests pass? Does the app start? (If not, this is a BROKEN state.)

### 3. Pick ONE action

**Priority framework: BROKEN > MISSING > DEPTH > POLISH**

When something is broken (tests fail, app won't start, regression), fix it first. When a core feature is missing, build it. When existing features need hardening, deepen them. Polish is last.

**Decision rules — first match wins:**

| Condition | Action | Invoke |
|-----------|--------|--------|
| Tests failing or app won't start | FIX | `/build` (with fix context) |
| No feedback files exist | RESEARCH | `/research` |
| Latest feedback suggests goal is wrong | FLAG | Output warning, suggest `/refine-goal`, stop |
| Feedback has spec changes not yet applied | ALIGN | `/align` |
| Specs describe features code doesn't have | BUILD | `/build` |
| Every 10th cycle: full evaluation due | EVALUATE | `/evaluate` |
| Every 5th cycle: focused evaluation due | EVALUATE | `/evaluate` (focused mode) |
| Every 5th cycle: structural/simplify due | SIMPLIFY | `/simplify` |
| Everything aligned and built | EVALUATE | `/evaluate` (default fallback) |

**Structural work commitment:** Every 5th cycle, regardless of backlog, do structural work (/simplify with strong mandate). This prevents the "structural debt deferred forever" problem. Don't skip it because there's a feature to build.

**Diminishing returns detection:** If the last 3 cycles were all DEPTH or POLISH (no BROKEN or MISSING), high-impact work is exhausted. Output: "High-impact work done. Recommend reducing to `/loop 2h /self-improve` or `/loop 4h /self-improve`." Don't keep burning budget on marginal improvements.

### 4. Invoke the skill

Use the Skill tool to invoke the chosen skill. The specialized skill handles execution, subagent launching, file writing, and committing.

### 5. Post-build verification

After any BUILD or FIX action completes:
- Run tests (if they exist)
- Verify the app starts
- If the project has a deploy step, run a quick smoke test after deploy
- If anything broke, the NEXT cycle's state will be BROKEN and it auto-prioritizes

### 6. Log (the handoff contract)

Append to `.claude/loop-log.md`:

```markdown
## YYYY-MM-DD HH:MM — Cycle N — ACTION
Pace: NORMAL | 5h: X% | 7d: Y% | Budget: Z%
What: [one sentence — what was done]
Result: [one sentence — what changed]
Tests: [pass count or "no tests"]

### Backlog (for next cycle)
1. [Highest priority remaining item]
2. [Second priority]
3. [Third priority]
```

**The backlog section is the handoff contract.** It tells the next cycle exactly what to focus on without re-reading everything. 3 items max. Update every cycle.

**Three sources of truth — don't duplicate between them:**
- `reference-docs/` (specs + goal) = what the project SHOULD be (intent)
- The code = what the project IS right now (state)
- `.claude/loop-log.md` = why things changed (decisions)

The log should never list features or restate the spec. It records actions, reasoning, and the backlog. After 50 entries, summarize the oldest 40 into a single "history summary" block at the top.

**Never lose the backlog.** If you're unsure what to do, read the last backlog entry. It's the previous cycle's best judgment about what matters next.
