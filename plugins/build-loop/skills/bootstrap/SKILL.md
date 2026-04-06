---
name: bootstrap
description: Generate starter reference-docs/ specs from an existing codebase. Run once when adding build-loop to an existing project.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Agent Write
effort: high
---

# Bootstrap — Onboard an Existing Project

You generate starter specs in `reference-docs/` by reading an existing codebase. This removes the "spec onboarding tax" — users don't have to manually reverse-engineer their project into docs before the loop can work.

Run this once when adding build-loop to a project that already has code.

## What to do

1. **Read the codebase.** Use Glob and Grep to understand the project:
   - What language(s)? Check file extensions, package files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.)
   - What's the entry point? (`main.*`, `app.*`, `index.*`, `cli.*`)
   - What's the directory structure? (`src/`, `lib/`, `tests/`, `static/`, etc.)
   - Is there a README? Read it.
   - Is there an existing CLAUDE.md? Read it — it may already describe the architecture.
   - Are there tests? What framework?

2. **Generate `reference-docs/architecture.md`:**
   - Project type (web app, CLI, library, API, etc.)
   - Key directories and what they contain
   - Entry points and main flows
   - Dependencies and their roles
   - How to run, test, and build

   Keep it factual — describe what IS, not what should be. Under 100 lines.

3. **Generate `reference-docs/conventions.md`** (if patterns are detectable):
   - Code style (inferred from existing code)
   - Naming conventions
   - Error handling patterns
   - Test patterns
   
   Only include what you can actually see in the code. Don't invent conventions.

4. **Do NOT generate `goal.md` or `evaluation.md`.** Those are per-session and set by the user via `/refine-goal` and `/refine-evaluation`. You're documenting what exists, not deciding what to build.

5. **Output a summary** of what was generated and suggest next steps:
   ```
   Bootstrap complete. Generated:
   - reference-docs/architecture.md (X lines)
   - reference-docs/conventions.md (Y lines)
   
   Next steps:
   1. Review the generated specs — fix anything wrong
   2. Run /refine-goal to set your pain and direction
   3. Run /refine-evaluation to define how to measure success
   4. Start the loop: /loop 30m /self-improve 20
   ```

## Rules

- **Describe, don't prescribe.** You're documenting the existing project, not redesigning it.
- **Be concise.** A 50-line architecture doc is better than a 300-line one. The code is the source of truth for detail.
- **Don't touch existing reference-docs/.** If specs already exist, note what you found and suggest updates — don't overwrite.
- **Skip what you can't infer.** An empty conventions.md is better than a made-up one.
