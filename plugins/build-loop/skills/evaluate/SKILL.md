---
name: evaluate
description: Test the product against the evaluation criteria. Supports full (3 agents), focused (1 agent), and checklist (no agents) modes.
argument-hint: [full|focused|checklist]
context: fork
agent: general-purpose
allowed-tools: Read Grep Glob Bash Agent Write
effort: high
---

# Evaluate — Would Real People Use This?

## Session paths
Goal: `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md`
Evaluation: `reference-docs/sessions/${CLAUDE_SESSION_ID}/evaluation.md`
Output: `reference-docs/sessions/${CLAUDE_SESSION_ID}/feedback-eval-YYYY-MM-DD.md`

## Three modes

Parse `$ARGUMENTS` for mode. Default: `focused`.

**`full`** (every 10th cycle — expensive, broad):
- Launch 2-3 sonnet subagents with distinct fresh personas
- Each reviews the full product (README, code, landing page, specs)
- Each answers: would you use this daily? Would you pay? Painkiller or vitamin?

**`focused`** (every 5th cycle — moderate, targeted):
- Launch 1 sonnet subagent
- Focuses on recent changes only (`git log -5`, `git diff HEAD~3`)
- Did recent work help? Any regressions?

**`checklist`** (any cycle — cheap, no agents):
- No subagents launched. You do the eval yourself by checking:
  - [ ] Does the README explain what this does in 60 seconds?
  - [ ] Do tests pass?
  - [ ] Does the app start?
  - [ ] Does the latest feedback have unaddressed items?
  - [ ] Is this still a painkiller? Name the pain in one sentence.
  - [ ] Would someone pay for this? Why?
- Write findings inline. Costs almost nothing.

**Use checklist when budget is tight or findings have converged.** Use full only when fresh eyes are needed. Default to focused.

## Convergence detection

Read previous feedback files. If the last 2 evaluations both had empty "New Findings Only" sections: output "Evaluation converged — further evals are waste. Switching to checklist mode only." Tell /self-improve to stop scheduling full/focused evals until new features ship.

## Output format

Write to `reference-docs/sessions/${CLAUDE_SESSION_ID}/feedback-eval-YYYY-MM-DD.md`:

```markdown
# Evaluation — YYYY-MM-DD (full/focused/checklist)

## Verdict: [PAINKILLER / VITAMIN / UNCLEAR]

## Findings
[For full/focused: persona findings. For checklist: checklist results.]

## What to Build Next
[ONE thing]

## New Findings Only
[What's new. If nothing: "Findings converged."]
```

## Rules
- Don't re-run same personas. Fresh each time.
- Don't evaluate code quality — that's /simplify.
- Simulated feedback ≠ real feedback. Note this.
