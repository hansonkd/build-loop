---
name: evaluate
description: Test the product against the evaluation method defined in evaluation.md. Launch sonnet subagents as target users. Called by /self-improve.
context: fork
agent: general-purpose
allowed-tools: Read Grep Glob Bash Agent Write
effort: high
---

# Evaluate — Would Real People Use This?

Launch sonnet subagents that test the product using this session's evaluation method.

## Session isolation
Read goal from `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md`. Read evaluation method from `reference-docs/sessions/${CLAUDE_SESSION_ID}/evaluation.md`. Write results to `reference-docs/sessions/${CLAUDE_SESSION_ID}/feedback-eval-YYYY-MM-DD.md`. Also scan other sessions' feedback for relevant findings.

## Two modes

**/self-improve passes a mode: "full" (every 10th cycle) or "focused" (every 5th cycle).**

**Full evaluation (every 10th cycle):**
- Launch 3 sonnet subagents with distinct personas matching the target user
- Each reviews: landing page, app code/UI, README, reference-docs
- Each answers the full evaluation criteria from `evaluation.md`
- Broad coverage — tests the whole product from fresh eyes

**Focused evaluation (every 5th cycle):**
- Launch 1-2 sonnet subagents
- Each focuses on ONE thing: the most recent changes (read `git log -5` and `git diff HEAD~3`)
- Did the recent work make the product more useful? Did it introduce regressions?
- Narrower but catches drift faster

Focused evaluations are cheaper and catch regressions. Full evaluations are expensive but prevent tunnel vision. Don't run full evaluations every cycle — they become repetitive after 6-8 rounds on the same codebase.

## What to do

1. Read this session's `goal.md` for the **Pain** and target user.
2. Read this session's `evaluation.md` for the full evaluation method.
3. Read this session's previous feedback files to avoid repeating the same findings.

4. Launch sonnet subagents. Each gets:
   - The evaluation method (tells them how to test)
   - A distinct, realistic persona matching the target user
   - Access to: landing page, app code, README, reference-docs
   - Instruction: "Answer honestly. Would you use this daily? Would you pay? What's missing? Is this a painkiller or a vitamin?"
   - **Critical:** "Don't evaluate the architecture or code quality. Evaluate whether this solves a real pain."

5. Synthesize into `reference-docs/sessions/${CLAUDE_SESSION_ID}/feedback-eval-YYYY-MM-DD.md`:

```markdown
# Evaluation — YYYY-MM-DD (full/focused)

## Verdict: [PAINKILLER / VITAMIN / UNCLEAR]

## Persona Findings
### [Persona 1 name + role]
- Would use daily: [YES/NO]
- Would pay: [YES/NO, how much]
- Top complaint: [one sentence]
- Top praise: [one sentence]

### [Persona 2] ...

## Consensus Issues
1. [Issue flagged by most personas]
2. ...

## What to Build Next
[The ONE thing that would most move the needle toward daily use]

## New Findings Only
[What's new that previous evaluations didn't catch. If nothing new: "Findings converged — consider reducing evaluation frequency."]
```

## Avoid these failure modes

- **Don't re-run the same personas.** Generate fresh ones each time. Reusing personas produces repetitive feedback.
- **Don't evaluate code quality.** That's /simplify's job. Evaluate whether the product solves a pain.
- **Don't over-evaluate.** If "New Findings Only" is empty two cycles in a row, evaluations are exhausted. Tell /self-improve to reduce frequency.
- **Don't let simulated users substitute for real ones.** Simulated feedback is useful for direction-setting but doesn't prove market fit. Note this in every evaluation.
