# HN Persona Feedback Round 3 — 2026-04-05

Personas: VP of Compliance (compliance_karen), SRE (sre_on_call), Competing AI startup founder (founder_of_rival)

## Strategic Insights (new this round)

### 1. EU AI Act Article 12 is the most urgent market opportunity
Full enforcement in August 2026 — 4 months away. Every high-risk AI deployment in the EU needs logging that Glass nearly satisfies. Frame Glass as "Article 12-compliant logging layer for high-risk AI systems." This opens doors compliance buyers can't ignore.

### 2. The proof bundle is the actual moat — not the crypto
No competitor (Langfuse, Helicone, Lunary) offers a portable, offline-verifiable proof artifact. The combination of local-first + proof bundle is defensible. Competitors can replicate the hash chain in a sprint; the product conviction behind "portable proof" is harder to steal.

### 3. Glass needs to be a library, not just a service
The CTO/SRE consensus: @glass.audit decorator wrapping existing LLM calls > replacement service. Current architecture requires rearchitecting your app around Glass. A Python SDK is the developer wedge.

### 4. The 6-12 month window is real
Once the proof bundle concept propagates through HN, established players will clone it. Glass needs either a hosted commercial tier or an acquisition path to a GRC vendor (Drata, Vanta, Hyperproof) within 90 days.

## Critical Issues (new findings)

### From compliance_karen
- Auditors don't accept ad-hoc JSON — need PDF export with header, signature block, control reference
- Proof bundle needs: control_refs, retention_class, legal_hold, reviewed_by fields
- Need population report endpoint (all queries in a period for auditor sampling)
- Need control mapping document: Glass feature → SOC 2 control → evidence type
- "Verified" label is a material misrepresentation in regulated contexts — auditor finding if used in evidence
- Vendor security questionnaire needed for procurement (table stakes)

### From sre_on_call
- No structured logging at all — zero JSON log lines, no request IDs, no correlation
- Health endpoint conflates liveness and readiness (need /healthz + /readyz split)
- LLM failures mid-pipeline produce zero audit records — request vanishes silently
- httpx clients create new TCP+TLS connection per request (no pooling)
- detect_backend() 3-second probe on every request (cache at startup)
- No graceful shutdown config — 120s LLM timeout vs 5s default uvicorn drain
- No Dockerfile, no k8s manifests
- WAL mode on SQLite is one line and not there

### From founder_of_rival (competitive analysis)
- Glass's differentiators vs Langfuse/Helicone: claim-level verification, portable proof bundles, premise flagging, process-first UX
- The verification circularity is the product's biggest competitive liability
- Open source without commercial tier = giving concepts away (proof bundle will be cloned)
- Local-first + proof bundle combination is the actual moat, not the cryptography alone
- Best competitive positioning: "The only AI tool where your auditor needs no account, no internet, and no trust in us"

## Refined Target User Profiles

### Primary: Compliance teams at AI-using companies (NEW — upgraded from secondary)
- VP of Compliance, GRC analysts, legal teams
- Need: audit artifacts, control mapping, population reports, PDF exports
- Buy because: EU AI Act Article 12, SOC 2 CC7.2, HIPAA 45 CFR 164.312
- Willingness to pay: HIGH ($20K-100K/year for compliant tooling)

### Secondary: Multi-agent AI developers
- Need: debug agent behavior, prove what agents actually did
- Buy because: "sanitized optimism" — agents lie about fixing bugs
- Willingness to pay: MEDIUM (comparable to Langfuse/Helicone pricing)

### Tertiary: Regulated enterprises in air-gapped/sovereign environments
- Government, defense, critical infrastructure
- Need: local-only AI with verifiable audit trails
- Buy because: data sovereignty mandates
- Willingness to pay: VERY HIGH (but long procurement cycles)

## Priority Stack for Next Build Cycle

Based on all 11 personas across 3 rounds, ranked by frequency + strategic impact:

### Tier 0 — Do before anything else
1. Rename "Verified" → "Consistent" (flagged by 11/11 personas)
2. Fix content_hash truncation to 32+ chars (flagged by 8/11)
3. Fix demo link / host a live demo (flagged by 7/11)

### Tier 1 — Foundation
4. WAL mode on SQLite + check_same_thread=False
5. Cache detect_backend() at startup
6. Handle LLM failures in audit trail (don't silently drop)
7. Extract _call_llm to shared module
8. Add 5 basic unit tests

### Tier 2 — Production readiness
9. Module-level httpx client (connection pooling)
10. Structured JSON logging middleware
11. Split /healthz and /readyz endpoints
12. Dockerfile + basic k8s manifest
13. Bearer token auth on API
14. Cloud confirmation gate before first send

### Tier 3 — Compliance market
15. PDF export for proof bundles
16. Population report endpoint
17. Control mapping document (SOC 2, ISO 27001, EU AI Act)
18. Compliance metadata fields on proof bundle
19. RFC 3161 external timestamping

### Tier 4 — Growth
20. Python SDK with @glass.audit decorator
21. Example query chips in UI
22. SSE streaming for real pipeline progress
23. Accessibility fixes (keyboard nav, contrast, ARIA)
