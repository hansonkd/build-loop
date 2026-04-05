# Glass — Principles

These are hard constraints. All code generation must adhere to every principle. If a design decision conflicts with a principle, the principle wins.

## 1. Honest by Structure, Not Instruction

Verification is architectural, not prompt-engineered. A separate verifier process checks claims independently of the generator. Prompting the generator to "be honest" is not a substitute for structural verification.

- Every response passes through a decomposition step that extracts individual claims
- Each claim is independently assessed by a verifier
- "I don't know" is a first-class output displayed prominently -- never hidden, never apologetic
- The system never presents unverified claims as verified

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
- If the user pushes back on a verified claim, the system holds its ground and shows evidence

## 4. Local-First, User-Owned Data

The default mode of operation requires no internet connection and sends no data to external services. Cloud backends are opt-in, clearly labeled, and never silent.

- Ollama is the default inference backend -- models run on the user's hardware
- All memory and conversation history is stored in a local SQLite database
- The user can inspect, export, edit, and delete any stored data at any time
- If a cloud API (e.g., Claude, OpenRouter) is used, the UI displays a persistent, prominent indicator that data is leaving the machine, including the exact destination
- No telemetry, no analytics, no phoning home
- The data flow panel shows exactly what bytes left the machine, where they went, and what came back -- for every operation

## 5. Verifiable Over Impressive

The system prioritizes narrow correctness over broad fluency. A response that says "I can verify X but not Y" is better than one that confidently covers everything.

- Claims are tagged: `verified` (evidence found), `uncertain` (plausible but unconfirmed), `unverifiable` (cannot be checked)
- The system prefers shorter, more precise answers over longer, more comprehensive ones
- When the model would need to speculate to answer fully, it answers partially and labels the gap
- No claim is presented without a confidence tag

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
