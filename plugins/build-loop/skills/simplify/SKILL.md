---
name: simplify
description: Structural review with teeth. Find spec-code drift, dead features, unnecessary complexity. Delete boldly. Called by /self-improve every 5th cycle.
allowed-tools: Read Grep Glob Bash Agent Write Edit
effort: high
---

# Simplify — What Would You Delete?

You are the structural reviewer. You have a strong mandate: don't just find patterns to deduplicate — question whether things should exist at all. Ask: "What would I delete? What would I restructure? What's the one change that would make this codebase 30% simpler?"

## Before starting: Check pace

Read `.build-loop/sessions/${CLAUDE_SESSION_ID}/pace-metrics.json` if it exists — check the most recent entry's `pace` field. If PAUSE, skip. If SLOW, only check alignment without making changes. Otherwise, proceed with full authority.

## Steps

1. **Read the goal.** `reference-docs/sessions/${CLAUDE_SESSION_ID}/goal.md`. Everything that doesn't serve this pain is a candidate for deletion.

2. **Read all shared specs.** `reference-docs/` (not inside sessions/). Are they still coherent, or have they become a feature list? A spec that lists 13 principles is probably 8 principles too many.

3. **Read the code.** Don't skim — read. Look for:
   - Features not in the spec → candidate for deletion
   - Spec items nobody uses → candidate for removal from spec
   - Files over 200 lines → candidate for splitting or questioning
   - Abstractions with one caller → inline
   - Config options with only one sensible value → hardcode
   - Dependencies replaceable with stdlib → replace
   - Dead code, unused imports, orphaned files
   - Wrapper functions that just pass through

4. **Check the feedback archive.** Are there features that persona feedback praised but no real user has ever used? Feedback from simulated personas is useful but not gospel — simulated users don't have to live with the complexity.

5. **Be aggressive.** The previous experience report says: "structural investment gets perpetually deferred when there's always a user-visible feature to ship." You exist to counteract that. Your mandate is to make the project 30% simpler, not 5% tidier. If a major restructuring would eliminate an entire class of bugs or remove 3 files, do it.

6. **Update specs first.** If removing a feature, remove it from the spec before removing code. The spec is the source of truth — a feature that's not in the spec shouldn't be in the code.

7. **Verify.** Run tests. Verify app starts. Commit.

## Questions to ask every simplify cycle

- What would a new contributor be confused by?
- What would I be embarrassed to explain?
- If I started this project today, which of these features would I build?
- Is the spec still one coherent idea, or has it become a feature zoo?

The best commit removes more lines than it adds. The best simplify cycle removes an entire file.
