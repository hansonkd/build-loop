# HN Persona Feedback Round 2 — 2026-04-05

Personas: frontend engineer (css_is_awesome), startup CTO (cto_at_series_b), OSS maintainer (oss_greybeard), tech journalist (tech_reporter_kate)

## Critical Consensus (raised by 3+ personas)

### 1. Demo link is broken — localhost:7777 in CTA
Every persona flagged this as disqualifying. Journalists can't write about it, HN readers can't try it, the CTA is a dead link for 100% of external visitors.

### 2. Fake pipeline animation is a trust contradiction
The loading pipeline stages (Generate → Decompose → Verify → Audit → Seal) advance on hardcoded setTimeout timers, not actual backend events. For a product about showing what AI "actually does," fabricated progress is the core contradiction. Need SSE streaming from backend.

### 3. Zero tests
No test files, no test directory, no pytest in dev deps. The hash chain verification — the project's core trust primitive — has no unit test. Five basic tests would transform credibility.

### 4. _call_llm duplication across decomposer.py and verifier.py
~85 lines copy-pasted verbatim. Classic LLM-generated code smell. Extract to shared glass/llm_client.py. Also _extract_json duplicated identically.

### 5. SQLite will break under concurrent use
No WAL mode, no check_same_thread=False, no connection pooling. Concurrent writes → OperationalError. An audit tool dropping audit records under load is self-defeating.

### 6. detect_backend() probes Ollama on every request
3-second timeout per request when Ollama is down. Cache at startup, refresh on interval.

## High-Priority Items by Persona

### From css_is_awesome (Frontend/UX)
- Fix WCAG AA contrast: --text-muted fails at 3.7:1, need 4.5:1+
- Claims not keyboard accessible (div onclick, no tabindex/role)
- No screen reader support on status badge or cloud banner
- Replace alert() with inline error states
- Flip column order on mobile (result first, process second)
- Add example query chips for empty state
- Move process-demo widget above fold on landing page

### From cto_at_series_b (Production readiness)
- Need Python SDK with @glass.audit decorator, not a replacement service
- SQLite needs WAL mode + connection pooling at minimum
- No auth on API endpoints — unacceptable for shared infrastructure
- Need explicit LOCAL_ONLY=true mode
- Claims/audit stored as JSON blobs, not queryable
- Backend detection should cache at startup, not probe per-request

### From oss_greybeard (Code quality)
- Extract _call_llm to shared module (3 copies across 3 files)
- Extract _extract_json (2 identical copies)
- Silent error swallowing on JSON parse failures (no logging)
- README port mismatch (says 5000, code defaults 7777)
- Claim.status should be Literal type, not plain str
- No CONTRIBUTING.md, no CI, no linter config
- Memory table exists in schema but write path never implemented

### From tech_reporter_kate (Positioning/narrative)
- Lead with "process-first UI" not "cryptographic proof" — the crypto creates credibility liability
- The verification circularity will be the headline if not disclosed
- Fix demo, rename Verified, add self-attestation disclosure BEFORE any press
- Compliance angle (healthcare, legal, finance) is highest-value press story
- Op-ed angle: "I built an AI tool assuming the AI company was lying to me"
- Add one sentence disclosing seal limitation on landing page

## Target User Profile (refined)

**Primary (from cto_at_series_b + shipfast_sarah round 1)**:
Developers building multi-agent AI systems who need to debug agent behavior — "the agent said it fixed the bug but it didn't" problem.

**Secondary (from tech_reporter_kate + cto_at_series_b)**:
Compliance teams in regulated industries (healthcare, legal, finance) who need auditable AI paper trails for governance mandates.

**Key insight from journalist**: The strongest press angle is cultural, not technical. "AI you can watch" resonates because it maps onto the 2024-2026 trust collapse. Lead with the story, not the cryptography.

## What's Working (praised across personas)

- Two-column process-first layout is genuinely novel and immediately communicable
- "Unverifiable" as first-class output is epistemically honest
- Minimal dependency chain (fastapi + uvicorn + httpx)
- No telemetry found in source
- Architecture doc matches the code (rare)
- Proof bundle concept is legitimate for compliance use cases
- Cloud banner with exact destination is honest design
- The cultural framing (built in response to documented incidents) is defensible and resonant
