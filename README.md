# build-loop

Autonomous product development skills for Claude Code. Set a goal, start the loop, and your project evolves while you sleep.

## Install

```bash
# Add the marketplace
/plugin marketplace add hansonkd/build-loop

# Install the plugin
/plugin install build-loop@build-loop-marketplace
```

Or install directly from a local clone:

```bash
git clone git@github.com:hansonkd/build-loop.git
/plugin install ./build-loop
```

## Quick Start

```bash
# 1. Set your goal (interactive — it will ask you questions)
/refine-goal

# 2. Define how to evaluate success (interactive)
/refine-evaluation

# 3. Start the loop — 20% budget, every 30 minutes
/loop 30m /self-improve 20
```

Or do it all in one shot:

```bash
/loop 30m /self-improve 20 "Help developers catch AI-generated bugs before merge"
```

The loop will create session-scoped goal and evaluation files, then start working.

## Named Sessions

Each Claude session gets its own goal, evaluation criteria, feedback, and log — so multiple sessions can work on the same project with different missions. Session state lives at `reference-docs/sessions/<session-id>/`.

**Named sessions make this much easier to manage:**

```bash
# Start a named session
claude -n "feature-auth"

# Or rename the current session at any time
/rename feature-auth

# You can also rename from the session picker
/resume  # then press R on any session to rename it
```

Without named sessions, you get auto-generated session IDs that are harder to track.

## What It Does

Each cycle, `/self-improve` checks your budget, reads the current state, and picks the single most valuable action:

```
/self-improve (router, runs every cycle)
    ├── /research      — gather external signals → feedback file
    ├── /evaluate      — sonnet subagents test product as target users
    ├── /align         — update specs from feedback (no code changes)
    ├── /build         — implement one change from spec, test, commit
    └── /simplify      — structural review, delete what doesn't serve the goal
```

**Priority: BROKEN > MISSING > DEPTH > POLISH**

The loop is spec-driven. Feedback updates specs. Specs drive code. Code never drifts from specs.

## Skills

### Autonomous (used by the loop)

| Skill | What it does | When it runs |
|-------|-------------|--------------|
| `/self-improve` | Router — checks budget, picks action, delegates | Every cycle |
| `/research` | Scans HN digests, GitHub issues, external sources | When no feedback exists |
| `/evaluate` | Launches sonnet agents as target users to test the product | Full every 10th cycle, focused every 5th |
| `/align` | Turns feedback into spec updates | When feedback has unapplied changes |
| `/build` | Picks highest-impact spec gap, implements, tests, commits | When specs describe unbuilt features |
| `/simplify` | Deletes code/specs that don't serve the goal | Every 5th cycle (mandatory) |

### Interactive (you run these)

| Skill | What it does |
|-------|-------------|
| `/refine-goal` | Set or update the project's goal — what pain you're solving |
| `/refine-evaluation` | Define how the loop should test if the product is working |

## How It Works

### Three Sources of Truth

| Question | Source |
|----------|--------|
| What should this be? | `reference-docs/` (shared specs) + session's `goal.md` |
| What is this now? | The code |
| Why did it change? | `.build-loop/sessions/<id>/loop-log.md` |

### The Goal File

Each session's goal lives at `reference-docs/sessions/<session-id>/goal.md`. It's the anchor — everything this session does derives from it:

```markdown
# Goal

**Pain:** Frontend developers waste 30% of review time on AI-generated bugs
**Solution:** A GitHub App that catches AI-specific bug patterns before merge
**Budget:** 20% of subscription capacity
**Not:** Not a general linter. Not a code formatter. Not an AI coding assistant.
**Set:** 2026-04-05
```

### The Evaluation File

Each session's evaluation method lives at `reference-docs/sessions/<session-id>/evaluation.md`. It can be as detailed as you want — personas, scenarios, success criteria:

```markdown
# Evaluation

## Target Personas
### Sarah — solo SaaS developer
- Uses Cursor + Claude daily, ships 3-5 PRs/day
- Pain: spends 30% of time reviewing AI code for subtle bugs
- Would pay $49/month if it saved 1 hour/day

## Test Scenarios
1. Read the landing page cold. Can you explain what this does in 10 seconds?
2. Follow the README to install. Where did you get stuck?
3. Would you come back tomorrow?

## Success Criteria
- 2/3 personas say they'd use this daily
- 2/3 would pay $20+/month
- Nobody says "this is a vitamin"
```

### Budget Management

The loop monitors your Anthropic rate limits via `claude-rate-monitor` and adjusts pace automatically:

```
NORMAL    — full speed, all skills available
SLOW      — only /evaluate runs, cheaper models
PAUSE     — skip cycle, wait for rate limit reset
```

It also infers other Claude sessions sharing your subscription and adjusts its budget share. No coordination needed — each session observes the shared rate limit independently.

## The Painkiller Test

Every skill asks before doing work:

1. **Is this a painkiller or a vitamin?** Painkillers solve active pain. Vitamins are nice improvements. If it's a vitamin, stop.
2. **Would someone pay with their own credit card?** Not their company's compliance budget. Their own money.
3. **What specific pain does this eliminate?** Name it in one sentence. If you can't, pick something else.
4. **Does this make people more effective, or just safer?** Build effectiveness. Safety is a feature, not a product.

## Examples

### Start a new project from scratch

```bash
# In an empty repo
/refine-goal
# > "What pain are you solving?"
# > "Developers waste hours picking the right local AI model for their task"

/refine-evaluation
# > Define personas, test scenarios, success criteria

/loop 30m /self-improve 20
# The loop creates reference-docs/, writes specs, builds code, evaluates, iterates
```

### Add the loop to an existing project

```bash
# In a repo with existing code
/refine-goal
# > Set the pain your project solves

/refine-evaluation
# > Define how to test if it's working

/loop 1h /self-improve 15
# The loop reads your code, gathers feedback, builds what's missing
```

### Run individual skills manually

```bash
/research              # Gather signals without the full loop
/evaluate              # Test the product right now
/build                 # Build the next highest-impact change
/simplify              # Clean up — what would you delete?
/align                 # Sync specs with latest feedback
```

### Run multiple sessions on the same project

```bash
# Terminal 1: build new features
claude --name "feature-builder"
# > /refine-goal  →  "Add OAuth login flow"
# > /loop 30m /self-improve 15

# Terminal 2: harden existing code
claude --name "hardener"
# > /refine-goal  →  "Find and fix edge cases in the API"
# > /loop 1h /self-improve 10

# Terminal 3: evaluate the product
claude --name "evaluator"
# > /refine-goal  →  "Test the product as target users, surface what's broken"
# > /loop 2h /self-improve 5

# Each session has its own goal, evaluation, and feedback
# All sessions share specs and code, coordinating through git commits
# Budget management infers other sessions and adjusts pace automatically
```

### Adjust the loop cadence

```bash
# Aggressive (early development, lots to build)
/loop 30m /self-improve 25

# Moderate (mid-development, diminishing returns kicking in)
/loop 2h /self-improve 15

# Maintenance (product is stable, just watching for drift)
/loop 6h /self-improve 10
```

## Dependencies

Installed automatically via the SessionStart hook:

- [`claude-rate-monitor`](https://www.npmjs.com/package/claude-rate-monitor) — reads Anthropic rate limit headers
- [`ccusage`](https://www.npmjs.com/package/ccusage) — reads Claude Code session token usage

Requires Node.js/npm for budget monitoring. If npm is not available, the loop runs without budget management (all cycles at NORMAL pace).

## License

MIT
