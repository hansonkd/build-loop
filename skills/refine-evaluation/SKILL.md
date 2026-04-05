---
name: refine-evaluation
description: Define or update how the self-improve loop evaluates the product. Writes reference-docs/evaluation.md.
disable-model-invocation: true
allowed-tools: Read Write Edit Bash
effort: medium
---

# Refine Evaluation — How Do We Know This Is Working?

You help the user define HOW the self-improve loop should evaluate the product. The evaluation method lives in `reference-docs/evaluation.md` — a full markdown file that can grow as detailed as needed.

## What to do

1. **Read `reference-docs/evaluation.md`** if it exists. Read `reference-docs/goal.md` for context on the pain.

2. **Show the user the current evaluation method** (or note that none exists).

3. **Help the user define or update it.** Ask:
   - "Who is the target user? What does their day look like?"
   - "If the product is working, what would a target user say about it?"
   - "What would make someone open this every day vs. try once and forget?"
   - "How should evaluation agents test? (read landing page as persona, try the demo, review code, check if they'd pay)"

4. **Write `reference-docs/evaluation.md`.** This file can be as long as needed. It might include:

   - Target personas with detailed backgrounds
   - Specific scenarios to test
   - Questions each evaluation agent must answer
   - What "success" looks like (concrete, not abstract)
   - What "failure" looks like
   - Competitors to compare against
   - Specific pain points to probe

   Example structure:
   ```markdown
   # Evaluation

   ## Target Personas
   ### Persona 1: Sarah, solo SaaS developer
   - Uses Cursor + Claude daily
   - Ships 3-5 PRs per day
   - Pain: spends 30% of time reviewing AI-generated code for subtle bugs
   - Would pay $49/month if it saved 1 hour/day
   
   ## Test Scenarios
   1. Read the landing page cold. In 10 seconds, can you explain what this does?
   2. Follow the README to install. How long? Where did you get stuck?
   3. Use the product on a real task. Did it help? Would you come back tomorrow?

   ## Success Criteria
   - 2/3 personas say they'd use this daily
   - 2/3 would pay $20+/month
   - Nobody says "this is a vitamin"

   ## Failure Signals
   - "I already do this with [existing tool]"
   - "Cool idea but I wouldn't actually use it"
   - "Who is this for?"
   ```

5. **Bad evaluation methods** (push back if the user suggests these):
   - "Check if the code is clean" — that's /simplify
   - "Review for security" — vitamin
   - "Make sure tests pass" — build step, not product evaluation
   - "Check best practices" — nobody pays for best practices

## The one question that matters
**Would a real person use this every day?**
