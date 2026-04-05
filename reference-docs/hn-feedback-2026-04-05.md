# HN Persona Feedback — 2026-04-05

Simulated reviews from four distinct HN personas. This file serves as input for the next build cycle.

## Consensus Issues (raised by 3+ personas)

### 1. "Verified" is a misleading label
**Every persona flagged this.** The verifier uses the same LLM that generated the response. "Verified" implies external ground truth; what we actually check is internal consistency. Rename to "Consistent" or "Self-consistent." Reserve "Verified" for claims checked against external sources.

### 2. Self-attestation problem with provenance seals
The hash chain proves the log wasn't modified after writing. It does NOT prove the log was accurate when written. Glass generates its own audit trail — a lying process produces a valid seal over lies. Be explicit about what the seal proves and doesn't prove, in the UI, docs, and proof bundle.

### 3. Cloud fallback is not truly "opt-in"
`detect_backend()` silently falls through from Ollama → OpenRouter → Claude based on env vars. A stale `OPENROUTER_API_KEY` from another project causes silent cloud routing. Need a confirmation gate before first cloud send, not just a retrospective banner.

### 4. Demo link is broken for everyone
Landing page CTA links to `localhost:7777`. 100% of external visitors get connection refused. Either host a live demo or change the CTA.

### 5. `content_hash` truncation is a real bug
16 hex chars = 64-bit collision resistance. Birthday-attack territory. Change to at least 32 chars (128-bit) or use full SHA-256.

## High-Priority Actionable Items (by impact)

### From security_nihilist
- Fix content_hash to 32+ chars (trivial, high impact)
- Add RFC 3161 external timestamping on seals
- Sign proof bundles with Ed25519 instance keypair
- Rename "Verified" → "Consistent"
- Document what seal proves vs. doesn't prove

### From shipfast_sarah
- Fix demo link (host live or change CTA)
- Pick ONE target user (multi-agent developers or compliance teams)
- Add example queries to the app for first-time users
- Auto-verify seal on response load (don't hide behind button)
- Add GitHub link prominently on landing page
- Fix fake pipeline animation (hardcoded timers don't reflect reality)
- Surface history in the UI (endpoint exists, no UI)

### From alignment_phd
- Rename "Verified" → "Consistent" / "Self-consistent"
- Add external grounding tier (web search, knowledge base, or RAG)
- Use different model for verifier than generator
- Implement calibration measurement (what % of "verified" claims are actually correct?)
- Add tooltip explaining circularity on every claim badge
- Separate anti-sycophancy from architectural claims (it's prompt-based, not structural)

### From privacyfirst_dev
- Add `--local-only` flag / mode (refuse all external calls)
- Confirm before first cloud send per session
- Disclose multi-hop routing (OpenRouter → Anthropic) in audit trail
- Surface triple-send exposure in cloud banner (3 API calls per query)
- Log the `check_ollama()` probe call in audit trail
- Add warning to proof bundle that it contains the raw query text

## Target User Profiles (from shipfast_sarah)

**Primary**: Developers building multi-agent AI systems who have been burned by agents lying about fixing bugs ("sanitized optimism" problem).

**Secondary**: Compliance teams in regulated industries (healthcare, legal, finance) who need auditable AI paper trails.

**Tertiary**: Security engineers auditing AI supply chains post-LiteLLM-type incidents.

## What's Working Well (praised by multiple personas)

- Two-column process-first layout is genuinely novel UX
- Proof bundle export is legitimately useful for compliance
- Hash chain implementation is clean, simple, correct
- Minimal dependency chain (fastapi + uvicorn + httpx)
- No telemetry in the source
- Cloud banner with exact destination is honest design
- "Unverifiable" as first-class output is epistemically honest
- Premise flagging (checking user's query for false assumptions) is good
- Graceful degradation when no backend available
