---
name: refine-goal
description: Set or update the session's goal. Interactive — always involves the user.
disable-model-invocation: true
allowed-tools: Read Write Edit Bash Glob
effort: medium
---

# Refine Goal — What Pain Are We Solving?

You help the user define or update this session's goal. The goal lives in `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md` — a markdown file that can grow as detailed as needed. Each session has its own goal; specs and code are shared.

## The goal file

At minimum:

```markdown
# Goal

**Pain:** [One sentence. Who has what pain?]
**Solution:** [One sentence. What does this project do about it?]
**Budget:** [N% of subscription capacity]
**Not:** [What this project refuses to be.]
**Set:** [YYYY-MM-DD]
```

Can also include: Context, Target Users, Competitive Landscape, Scope Boundaries sections.

## What to do

1. **Read this session's goal** at `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md` if it exists. Show the user the current goal.

2. **If no goal exists**, create the session directory and help the user define one:
   - "What pain are you solving? Who has it?"
   - "Are people spending money on this today? On what?"
   - "What would you build that's NOT a drop-in replacement for existing tools?"
   - "What's the paradigm shift — what's newly possible that wasn't before?"

3. **If a goal exists**, ask what changed:
   - Check this session's loop-log for FLAG entries
   - Check this session's feedback files for goal-change suggestions
   - "Is the pain still right, or has something shifted?"

4. **Apply the painkiller test:**
   - Painkiller or vitamin? Push back if vitamin.
   - Would someone pay with their own credit card?
   - Is there a paradigm shift, or is this a better mousetrap?

5. **Update the goal file** with the user's input. Never rewrite without confirmation.

6. **If the goal changed**, note that shared specs in `reference-docs/` and this session's `evaluation.md` may need updating. Suggest `/refine-evaluation` if the target user changed.
