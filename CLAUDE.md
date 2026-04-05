# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A docs-driven code generation workflow. The user maintains project vision and specifications in `reference-docs/`. Claude reads those docs and generates/maintains a working project in `project/`.

## Directory Structure

- **`reference-docs/`** — The single source of truth. Contains the user's vision, specifications, architecture decisions, and any constraints for the project. Claude never modifies this directory.
- **`project/`** — The generated project (Glass). All code, configs, and assets Claude produces live here. Everything in this directory is derived entirely from `reference-docs/`. Runs the Glass app on port 7777 as a live demo, using OpenRouter as the LLM backend.
- **`landing-page/`** — A static landing page for the Glass project. Runs on port 80. Describes what Glass is, links to the live demo on port 7777.
- **`hackernews-ai-digest/`** — Git submodule. HN digest archive used for research. Do not modify.

## Core Workflow

**Before writing any code, always read every file in `reference-docs/`.**

1. Read all docs in `reference-docs/` to understand the current vision and specs.
2. If the docs are ambiguous, incomplete, or contradictory — **stop immediately**. Tell the user exactly what's unclear and ask them to update the docs before continuing. Do not guess or fill in gaps.
3. If the docs are clear, generate or update files in `project/` to match the specification.
4. When updating existing code in `project/`, re-read the docs first to ensure changes stay aligned with the source of truth.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && cd project && pip install -e .

# Run Glass demo (port 7777)
cd project && OPENROUTER_API_KEY=... glass

# Run landing page (port 80)
python3 landing-page/serve.py

# Run both
python3 landing-page/serve.py & cd project && OPENROUTER_API_KEY=... glass
```

## Rules

- **Docs are authoritative.** If the code in `project/` contradicts `reference-docs/`, the docs win. Fix the code.
- **Never modify `reference-docs/`.** That's the user's domain. If the docs need changes, say so and stop.
- **Never invent features.** Only build what the docs describe. If a feature seems implied but isn't specified, ask rather than assume.
- **When in doubt, stop.** It's always better to ask the user to clarify the docs than to generate code based on assumptions.

## Evaluation Rules — The Painkiller Test

Every evolution cycle and every feedback round MUST ask these questions FIRST, before any technical evaluation:

1. **Is this a painkiller or a vitamin?** A painkiller solves a pain people have RIGHT NOW. A vitamin makes things theoretically better. If the project is a vitamin, stop and reconsider the entire direction before optimizing further.
2. **Would a real person use this daily?** Not "would they admire the architecture" or "would it satisfy an auditor" — would they open it every day because it makes them more effective?
3. **Would someone pay for this with their own money?** Not their company's compliance budget. Their own credit card. If not, the value prop is too abstract.
4. **What specific pain does this eliminate?** Name the pain in one sentence. If you can't, the project doesn't have product-market fit.
5. **Does this make people more effective, or just safer?** People buy effectiveness. Safety is a feature of effective tools, not a product category.

These questions override all technical feedback. A perfectly engineered product nobody wants is worse than a rough product everyone needs.
