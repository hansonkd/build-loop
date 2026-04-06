# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin that keeps your project moving between sessions. Set a goal, start the loop, and every cycle it researches, evaluates, builds, or simplifies — then writes a structured handoff so the next cycle (or you) knows exactly where to pick up.

## Plugin Structure

- **`plugins/build-loop/skills/`** — The skill files. This is the product.
- **`.claude-plugin/`** — Plugin manifest and marketplace config for installation.
- **`hooks/`** — SessionStart hook that auto-installs npm deps (`claude-rate-monitor`, `ccusage`).
- **`package.json`** — npm dependencies for budget monitoring.

## Skills

| Skill | Role | Cadence |
|-------|------|---------|
| `/self-improve` | Router — checks budget, picks action, delegates | Every cycle (30m default) |
| `/research` | Gathers external signals → feedback file | When no feedback exists |
| `/evaluate` | Sonnet subagents test product as users | Full every 10th, focused every 5th cycle |
| `/align` | Feedback → spec updates (no code) | When feedback has unapplied spec changes |
| `/build` | Spec → code, one change, test, commit | When specs describe unbuilt features |
| `/simplify` | Structural review — delete boldly | Every 5th cycle (mandatory) |
| `/refine-goal` | User sets the pain (interactive) | On demand |
| `/refine-evaluation` | User sets how to measure success (interactive) | On demand |

## Three Sources of Truth (in user projects)

| Question | Source |
|----------|--------|
| What should this be? | `reference-docs/` (specs + goal) |
| What is this right now? | The code |
| Why did it change? | `.build-loop/sessions/<id>/loop-log.md` |

## Priority Framework

BROKEN > MISSING > DEPTH > POLISH

## The Painkiller Test

Every skill asks: Is this a painkiller or a vitamin? Would someone pay with their own credit card? If not, stop and reconsider.

## Development

```bash
# Install npm deps (for budget monitoring)
npm install

# Test skills locally — install as a project plugin
/plugin install ./
```
