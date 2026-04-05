# Glass — Principles

These are hard constraints. All code generation must adhere to every principle. If a design decision conflicts with a principle, the principle wins.

## 1. Honest by Structure, Not Instruction

Consistency checking is architectural, not prompt-engineered. A separate checker process assesses claims against the reasoning that produced them. Prompting the generator to "be honest" is not a substitute for structural checking.

- Every response passes through a decomposition step that extracts individual claims
- Each claim is independently assessed by a consistency checker
- "I don't know" is a first-class output displayed prominently -- never hidden, never apologetic
- The system never presents unchecked claims as consistent
- Important limitation: the consistency checker uses the same type of LLM as the generator. "Consistent" means internally coherent, not factually correct. This is self-attestation, not independent verification.

## 2. Process-First Transparency

The process is the primary interface, not the answer. Users see the AI's work happening in real time -- every pipeline stage is visible as it executes, not hidden behind a spinner.

- The audit trail is displayed as a live timeline during query processing, not collapsed under a toggle after the fact
- Each pipeline stage (generate, decompose, verify) appears in the UI as it begins and completes, with timing and data flow visible
- The reasoning trace is presented as a first-class panel alongside the answer, not beneath it
- If the model's reasoning contains a contradiction, the UI highlights it rather than hiding it
- The summary answer is explicitly labeled as a convenience layer over the process -- the process is the proof

## 3. Anti-Sycophancy

The system is designed to disagree when disagreement is warranted. It does not optimize for user satisfaction -- it optimizes for accuracy.

- When the user's premise contains a factual error, the system flags it before answering
- Confidence scores reflect actual verification status, not rhetorical hedging
- The system never uses phrases like "Great question!" or "You're absolutely right!" -- it responds to content, not to the user's ego
- If the user pushes back on a consistent claim, the system holds its ground and shows evidence

## 4. Local-First, User-Owned Data

The default mode of operation requires no internet connection and sends no data to external services. Cloud backends are opt-in, clearly labeled, and never silent.

- Ollama is the default inference backend -- models run on the user's hardware
- All memory and conversation history is stored in a local SQLite database
- The user can inspect, export, edit, and delete any stored data at any time
- If a cloud API (e.g., Claude, OpenRouter) is used, the UI displays a persistent, prominent indicator that data is leaving the machine, including the exact destination
- No telemetry, no analytics, no phoning home
- The data flow panel shows exactly what bytes left the machine, where they went, and what came back -- for every operation

## 5. Consistent Over Impressive

The system prioritizes narrow correctness over broad fluency. A response that says "I can check X but not Y" is better than one that confidently covers everything.

- Claims are tagged: `consistent` (internally coherent with reasoning), `uncertain` (plausible but weakly supported), `unverifiable` (cannot be assessed from available information)
- "Consistent" means the claim is self-consistent with the reasoning trace, not that it is factually verified against external sources. The same type of LLM is used for generation and consistency checking — this is self-attestation, not independent verification.
- The system prefers shorter, more precise answers over longer, more comprehensive ones
- When the model would need to speculate to answer fully, it answers partially and labels the gap
- No claim is presented without a status tag

## 6. Auditable Actions

Every action the AI takes is logged, timestamped, and visible to the user. The audit trail is immutable, inspectable, and prominently displayed.

- Every LLM call is logged with: the prompt sent, the backend used, the tokens consumed, the latency, and a hash of the response
- Every external network request is recorded: destination, method, payload size, and whether it succeeded
- The audit trail is stored locally alongside the response data and is never sent externally
- The UI presents the audit trail as the primary evidence of what Glass did -- it is the first thing the user sees after the answer, not the last
- If the system takes an action the user did not explicitly request, the audit trail flags it as "implicit"
- The audit trail is the proof that Glass is doing what it claims -- if the trail is empty, no action was taken
- Local operations are visually distinguished from external operations at a glance (green vs amber)

## 7. Provenance Seals

Every response carries a cryptographic hash chain that proves the audit trail has not been altered. Trust is verified, not assumed.

- Each audit event is hashed with a reference to the previous event's hash, forming a chain
- The final seal (chain head hash) is displayed in the UI and stored with the response
- Anyone can verify the seal by recomputing the chain from the raw audit events -- no trust in Glass required
- The seal covers: every LLM call hash, every timestamp, every byte count, and the final response content
- If any event in the chain is modified, inserted, or removed, the seal breaks and the UI shows it
- The provenance seal is not encryption or DRM -- it is a receipt. The user owns it. It proves what Glass did, to anyone, at any time
- The seal is computed locally and never requires an external service

## 8. Portable Proof

Every response can be exported as a self-contained proof bundle that anyone can verify independently, without Glass running. Trust is not trapped inside the application.

- The proof bundle is a single JSON file containing: the query, the full response, all claims with verification status, the complete audit trail, the provenance seal, and a description of the verification algorithm
- The bundle is downloadable from the UI with one click and from the API with one GET request (JSON or PDF format)
- Anyone can verify the bundle by recomputing the SHA-256 chain from the raw events -- no Glass installation, no API key, no trust required
- The bundle is human-readable: every field is labeled, every operation is described in plain language, timestamps are ISO 8601
- The bundle includes a `verification_instructions` field that describes the exact algorithm to verify the seal, so a third party can write their own verifier
- The bundle never contains secrets, API keys, or identifying information about the user -- only the process and its proof
- Export is always available, even when no backend is connected -- proof of past responses is never gated behind a running service

## 9. Empirical Calibration

Glass measures its own accuracy empirically. When Glass says "consistent", it should be possible to ask: how often is that actually true? Calibration is the bridge between self-attestation and external validation.

- Human reviewers can submit ground-truth judgments for any past claim
- The calibration system computes per-status accuracy: what fraction of "consistent" claims were actually correct?
- The calibration gap (difference between implied 100% and actual accuracy) is exposed via API, never hidden
- Sample size sufficiency is reported: at least 30 judgments per status label for statistical significance
- Calibration improves over time through better models, tighter prompts, or domain-specific tuning -- and that improvement is measurable
- This is tedious empirical work, not a technical trick. It is the only honest answer to "how good is your transparency?"

## 10. No Simulated Transparency

Glass never fakes its own process. If a pipeline stage hasn't completed on the server, the UI must not show it as complete. Progress indicators reflect actual server-side state, not timers or animation.

- The SSE streaming endpoint emits real events as each pipeline stage completes
- The frontend renders these events as they arrive -- no setTimeout, no simulation
- A transparency tool that simulates its own transparency is a contradiction
- This principle extends to error reporting: if a stage fails, the failure is shown immediately, not masked

## 11. Access Control Without Obscurity

When deployed in production, Glass API endpoints require bearer token authentication. Security is not optional for a compliance tool.

- Set GLASS_API_TOKEN to enable auth on all /api/* endpoints
- Health probes (/healthz, /readyz) are always public (required for k8s/load balancers)
- Static assets (/, /static/*) are always public (required for browser loading)
- When no token is configured, Glass runs in open-access mode (local dev)
- Token comparison uses constant-time comparison to prevent timing attacks
- Auth is a security boundary, not an obscurity mechanism -- the tool remains open source and auditable

## 12. Cloud Confirmation Gate

No query data leaves the machine until the user explicitly confirms cloud data egress. Policy is a promise. Architecture is a guarantee.

- When GLASS_CLOUD_CONFIRM=1, cloud backends (openrouter, claude) are blocked until POST /api/cloud/confirm is called
- The gate resets every session -- confirmation is per-process, not permanent. Every deployment must consciously opt into cloud data flows
- Local backends (ollama) are never gated -- they send no data externally
- The frontend shows a modal overlay when the gate is active, requiring explicit user action before any query can be submitted
- The gate applies to both /api/query and /api/query/stream -- there is no way to bypass it
- This is the architectural answer to IBM "Bob" (HN Jan 2026): an agent tricked into auto-executing malware because the user clicked "always allow"

## 13. Multi-Model Verification

When configured, the consistency checker runs on a different model than the generator. This is the first step toward decoupling self-attestation from generation.

- Set GLASS_VERIFIER_BACKEND and optionally GLASS_VERIFIER_MODEL to use a separate model for verification
- The verifier backend is recorded in the response and proof bundle, making the separation auditable
- When not configured, Glass falls back to same-model verification (the existing self-attestation model)
- Multi-model mode does not claim to be "independent verification" -- it claims to be structurally less likely to share the same blind spots
- The audit trail shows which backend performed each LLM call, so the verifier's operations are distinguishable from the generator's
- This responds to the "LLM-as-a-Courtroom" signal (HN Jan 2026): adversarial or independent judgment produces more reliable decisions than single-model scoring
