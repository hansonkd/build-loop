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

## First run (zero-config quickstart)

If `$ARGUMENTS` has 2+ parts, parse as `<budget%> <goal-summary>`. Then:

1. Create session dirs
2. Write goal.md with the summary as the Pain field and budget
3. Write a starter evaluation.md with default method
4. **Auto-bootstrap:** If existing code but no shared specs, generate them by reading the codebase. Skip if specs exist.
5. Initialize loop-log with cycle 0
6. Run the first cycle immediately

After first run, read goal from goal.md — don't require it in cron args again.

If no goal file exists and no args: say "Run `/self-improve <budget%> <goal>` or `/refine-goal` first" and stop.

## Each cycle

### 1. Budget

Run `npx claude-rate-monitor --json`. If it fails or was checked < 5 minutes ago (check `.build-loop/sessions/${CLAUDE_SESSION_ID}/pace-metrics.json` timestamp), skip and use last known pace.

- 5h utilization > 0.8 → **PAUSE** (log and stop)
- 5h utilization > budget × 1.5 → **SLOW** (only /evaluate and small /build)
- Weekly > 0.85 with > 2 days left → **SLOW**
- Otherwise → **NORMAL**

### 2. Auto-cancel check

**If 3+ consecutive cycles were PAUSE or SKIP with no work done: stop the loop entirely.** Output: "Auto-cancelled — no work for 3 cycles. Restart with `/loop` when there's new input." Don't keep polling for nothing.

### 3. State

Read: loop-log (last backlog only — don't re-read everything), session feedback files, `git log --oneline -5`.

**Auto-summarize:** If loop-log exceeds 50 entries, summarize the oldest 40 into a history block before proceeding. Don't rely on remembering to do this.

### 4. Decide (first match wins)

**BROKEN > MISSING > DEPTH > POLISH**

| Condition | Action |
|-----------|--------|
| Tests failing / app broken | FIX → `/build` |
| No feedback for this session | RESEARCH → `/research` |
| Feedback says goal is wrong | FLAG → warn user, stop |
| Feedback has unapplied spec changes AND they're large | ALIGN → `/align` |
| Feedback has small spec changes | BUILD (update spec inline, then implement) |
| Specs have unbuilt features | BUILD → `/build` |
| Every 10th cycle | EVALUATE (full) → `/evaluate full` |
| Every 5th cycle (mandatory) | SIMPLIFY → `/simplify` (block BUILD until done) |
| 5+ cycles since last eval | EVALUATE (focused) → `/evaluate focused` |
| Everything aligned | EVALUATE → `/evaluate focused` |

**BUILD can update specs inline** for small changes (adding a field, fixing a description, one-paragraph additions). Don't force a separate ALIGN cycle for trivial spec updates. ALIGN is for when feedback requires rethinking multiple spec files.

**SIMPLIFY blocks BUILD** on its cycle. Don't skip it because there's a feature to build. The 5th-cycle commitment has teeth.

**SLOW allows small BUILD** — not just evaluate. If the change is < 20 lines and addresses a BROKEN or MISSING item, do it even at SLOW pace.

If last 3 cycles were all DEPTH/POLISH: flag diminishing returns and recommend reducing frequency.

### 5. Delegate

Invoke the chosen skill. Pass mode to evaluate: `/evaluate full` or `/evaluate focused`.

### 6. Log

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

The backlog is the handoff contract. 3 items max. Never lose it.
