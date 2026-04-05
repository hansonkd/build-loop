---
name: refine-goal
description: Set or update the project goal in reference-docs/goal.md. Interactive — always involves the user.
disable-model-invocation: true
allowed-tools: Read Write Edit Bash Glob
effort: medium
---

# Refine Goal — What Pain Are We Solving?

You help the user define or update the project's goal. The goal lives in `reference-docs/goal.md` — a markdown file that can grow as detailed as needed.

## The goal file

At minimum, `reference-docs/goal.md` has:

```markdown
# Goal

**Pain:** [One sentence. Who has what pain?]
**Solution:** [One sentence. What does this project do about it?]
**Budget:** [N% of subscription capacity]
**Not:** [What this project refuses to be.]
**Set:** [YYYY-MM-DD]
```

But it can also include detailed sections:

```markdown
## Context
Why this pain matters now. Market timing. What changed.

## Target Users
Detailed descriptions of who has this pain.

## Competitive Landscape
What they use today. Why it's not good enough. What the gap is.

## Scope Boundaries
Detailed "Not" list — features we refuse to build, markets we refuse to enter.
```

## What to do

1. **Read `reference-docs/goal.md`** if it exists. Show the user the current goal.

2. **If no goal exists**, help the user create one:
   - "What pain are you solving? Who has it?"
   - "Are people spending money on this today? On what?"
   - "What would you build that's NOT a drop-in replacement for existing tools?"
   - "What's the paradigm shift — what's newly possible that wasn't before?"

3. **If a goal exists**, ask what changed:
   - Check `.claude/loop-log.md` for FLAG entries from /self-improve
   - Check latest `feedback-*.md` for goal-change suggestions
   - "Is the pain still right, or has something shifted?"

4. **Apply the painkiller test:**
   - Painkiller or vitamin? Push back if vitamin.
   - Would someone pay with their own credit card?
   - Is there a paradigm shift, or is this a better mousetrap?

5. **Update `reference-docs/goal.md`** with the user's input. The user owns the goal — never rewrite it without confirmation.

6. **If the goal changed**, note that specs and `reference-docs/evaluation.md` may need updating. Suggest the user also runs `/refine-evaluation` if the target user changed.
