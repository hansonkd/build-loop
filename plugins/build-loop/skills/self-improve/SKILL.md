---
name: self-improve
description: Autonomous product development router. Checks budget, reads state, picks the single best action, delegates to a specialized skill. Use with /loop.
argument-hint: [budget-percent] [goal-summary]
allowed-tools: Read Grep Glob Bash Write Edit
effort: medium
---

# Self-Improve — Development Loop Router

Each cycle: check budget, read state, pick ONE action, delegate. You don't do the work.

## Session paths

Per-session: `reference-docs/sessions/${CLAUDE_SESSION_ID}/` (goal, evaluation, feedback) and `.build-loop/sessions/${CLAUDE_SESSION_ID}/` (loop-log, pace-metrics). Shared: `reference-docs/*.md` (specs) and the code. Coordination via git.

## First run

If `$ARGUMENTS` has 2+ parts, parse as `<budget%> <goal-summary>`. Create session dirs, write starter goal.md and evaluation.md, initialize loop-log with cycle 0.

If no goal file exists and no args: say "Run `/refine-goal` first" and stop.

## Each cycle

### 1. Budget

Run `npx claude-rate-monitor --json`. If it fails, skip budget check and run NORMAL.

- 5h utilization > 0.8 → **PAUSE** (log and stop)
- 5h utilization > budget × 1.5 → **SLOW** (only /evaluate)
- Weekly > 0.85 with > 2 days left → **SLOW**
- Otherwise → **NORMAL**

### 2. State

Read: loop-log (last backlog), session feedback files, other sessions' feedback, `git log --oneline -5`. Quick check: tests pass? App starts?

### 3. Decide (first match wins)

**BROKEN > MISSING > DEPTH > POLISH**

| Condition | Action |
|-----------|--------|
| Tests failing / app broken | FIX → `/build` |
| No feedback for this session | RESEARCH → `/research` |
| Feedback says goal is wrong | FLAG → warn user, stop |
| Feedback has unapplied spec changes | ALIGN → `/align` |
| Specs have unbuilt features | BUILD → `/build` |
| Every 10th cycle | EVALUATE (full) → `/evaluate` |
| Every 5th cycle | EVALUATE (focused) or SIMPLIFY → `/evaluate` or `/simplify` |
| Everything aligned | EVALUATE → `/evaluate` |

Every 5th cycle: mandatory structural work (/simplify). Don't defer it.

If last 3 cycles were all DEPTH/POLISH: "High-impact work done. Recommend reducing loop frequency."

### 4. Delegate

Invoke the chosen skill. It handles execution, subagents, commits.

### 5. Log

Append to `.build-loop/sessions/${CLAUDE_SESSION_ID}/loop-log.md`:

```markdown
## YYYY-MM-DD HH:MM — Cycle N — ACTION
Pace: X | 5h: X% | 7d: X% | Budget: X%
What: [one sentence]
Result: [one sentence]
Tests: [count or N/A]

### Backlog (for next cycle)
1. [Top priority]
2. [Second]
3. [Third]
```

The backlog is the handoff contract. 3 items max. Never lose it. After 50 entries, summarize the oldest 40.
