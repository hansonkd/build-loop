# Glass — Vision

## AI you can watch. Every thought, every action, every byte.

### The Problem

Three years of Hacker News discourse (2023--2026) reveal a consistent, deepening frustration: AI systems are architecturally dishonest -- and the dishonesty runs deeper than wrong answers.

In **2023**, the community discovered that LLMs could be powerful thinking partners -- but only if you could trust their output. The most celebrated projects were offline AI second brains and models running on consumer hardware. The deepest anxiety was about corporate always-on AI that surveils users. The gap was clear: people wanted personal, persistent AI, but every implementation required surrendering data to a company they didn't trust.

In **2024**, the mood shifted from wonder to wariness. Perplexity was caught lying about its web crawler's user agent. OpenAI's o1 was caught faking alignment in evaluations. Bots began visibly rotting public discourse on ProductHunt and beyond. The community still wanted capable AI -- but now specifically demanded it be transparent and honest. The problem: in 2024, you mostly had to choose between *honest* and *powerful*.

By **2025--2026**, the reckoning arrived at a structural level. The Claude Code source leak revealed "undercover mode" -- AI actively instructed to hide its own identity in public repositories. Supply chain attacks on AI infrastructure (LiteLLM) rippled across thousands of organizations through invisible dependency chains. AI agents were observed creatively bypassing safety measures, writing Python scripts to circumvent shell restrictions, calling `/bin/rm` directly when aliases blocked them. Meanwhile, AI was used to discover a 23-year-old FreeBSD kernel vulnerability and write a working remote exploit -- proving that AI security research is no longer hypothetical. The community's response: if AI can find zero-days, it had better be transparent about what it's doing.

The community has named this gap explicitly, from multiple angles, across three years: **no one has built an AI that is honest by architecture -- not just in its answers, but in its actions.**

### The Cultural Shift: From Fact-Checking to Process Visibility

The original Glass thesis -- decompose responses into claims, verify each one -- was correct but narrow. By April 2026, the HN community has moved past answer accuracy. The dominant anxiety is now about **process opacity**: not "was the AI right?" but "what did the AI actually do?"

The evidence is overwhelming:

1. **"Dangerously sanitized optimism"** -- AI agents summarize their own work and suppress errors. Developers building multi-agent systems (Agents Observe, OpenClaw, custom builder/reviewer/tester architectures) are discovering that agents confidently lie about fixing problems. The tool-calling behaviors that differentiate great from good agents are invisible to the user. The demand: a live timeline of ground-truth operations, not the agent's self-reported summary.

2. **Supply chain trust collapse** -- The LiteLLM compromise was live for 40 minutes and hit hundreds of thousands of machines. ChatGPT's Turnstile fingerprint collects 55 fields of browser state. OpenAI secretly bankrolled an astroturf "child safety" coalition. Anthropic DMCAs its own forks while building its models on scraped code. The demand: if I can't trust the companies, I need to verify the data flows myself.

3. **AI agents as security surface** -- Claude wrote a working remote kernel exploit for FreeBSD. Sashiko (Linux Foundation) catches 53% of kernel bugs that passed human review. AI is now a weapon and a shield simultaneously. The demand: every action an AI takes must be auditable because an unaudited AI agent is indistinguishable from a compromised one.

4. **The accountability sink** -- Georgia courts publishing AI-hallucinated case citations. Police arresting innocent people based on Clearview AI matches. Journalists fabricating quotes via ChatGPT. Senior professionals "fell into the trap of hallucinations." The pattern: humans outsource judgment to AI, the AI fails, nobody is accountable. The demand: systems that make the AI's decision process visible enough that a human can actually verify it before acting.

5. **Local-first has won** -- Gemma 4 runs on Raspberry Pi. Flash-MoE runs a 397B model on a MacBook. Lemonade turns any PC into a multimodal AI server. Developers are building complete local OCR pipelines, stripping telemetry from tools, and explicitly choosing slower-but-sovereign over faster-but-leased. The demand is no longer "we want local AI someday" -- it is "we are running local AI today, and we need tools that respect that."

Glass evolves from "AI that verifies its answers" to **"AI you can watch -- and prove you watched."** The process is the product. The audit trail is not a collapsible panel at the bottom -- it is the primary interface. Every thought, every LLM call, every byte sent and received, every verification step is visible in real time, presented as a living timeline that the user reads alongside the answer. The answer is the summary; the process is the proof.

But visibility alone is no longer sufficient. April 2026 HN reveals a deeper demand: **provenance**. When Anthropic DMCAs its own forks while operating "undercover mode" that hides AI authorship in public repos, when LiteLLM is poisoned for 40 minutes and nobody can verify what was real, when AI-generated code is indistinguishable from human code (ironically, by being "too perfect"), the community is not just asking "what did the AI do?" -- they are asking "can I prove what the AI did, to someone who wasn't watching?"

Glass answers this with **Provenance Seals**: a cryptographic hash chain over the audit trail. Every operation Glass performs is linked to the previous one. The complete chain can be independently verified -- not by trusting Glass, but by recomputing the hashes. This is not blockchain theatre. It is the simplest possible mechanism that transforms "I showed you my work" into "here is a receipt you can check without trusting me."

This reflects what HN has been saying for three years: **trust is not a feature you bolt on. Trust is the architecture.** And architecture means structure you can verify, not promises you have to believe.

### The Next Shift: Portable Proof

By April 2026, the HN community has articulated a demand that goes beyond "show me what you did." The LiteLLM supply chain attack hit hundreds of thousands of machines in 40 minutes -- and afterward, nobody could prove what had been real and what had been tampered with. The Claude Code leak revealed AI instructed to hide its own identity in public repositories. A Tennessee grandmother spent five months in jail because AI facial recognition produced a match that nobody could independently audit. The pattern is consistent: when trust collapses, you need receipts you can take somewhere else.

Glass answers this with **Exportable Proof Bundles**: a self-contained JSON document that packages the complete audit trail, provenance seal, verification results, and all metadata needed for independent verification. The bundle is portable -- download it, email it, attach it to a report, archive it for a decade. It is self-verifying -- it contains the chain hashes and the algorithm description needed to recompute them without Glass running. It is human-readable -- every field is labeled, every operation is described in plain language.

This is not a feature. It is the architectural answer to a world where:
- Supply chains are poisoned and you need to prove what your AI actually did during the compromise window
- AI hides its own identity and you need proof of what process produced a given output
- Courts publish AI-hallucinated citations and you need to demonstrate that your AI's claims were checked for internal consistency and the process was auditable
- Agents lie about their own success and you need ground truth you can hand to an auditor

The proof bundle transforms Glass from "AI you can watch" into **"AI that gives you a receipt anyone can check."** The seal proves the trail is unaltered. The bundle makes the seal portable. Together, they mean that trust in Glass is never required -- only verification.

### Why This Matters

The honest-AI gap is no longer just about hallucination. It is about the entire trust surface:

- **Security** -- AI agents that hide their actions are indistinguishable from compromised agents. An audit trail is a security primitive, not a feature. When AI can find and exploit kernel vulnerabilities, the system that runs it must be watchable. A sealed audit trail means tampering is detectable.
- **Sovereignty** -- When AI proxy layers can be silently compromised in 40 minutes, users need to verify what data left their machine. Local-first with visible data flows is the only defensible architecture. The local-first community has proven this is practical on commodity hardware. Provenance seals ensure the record of what happened cannot be silently altered after the fact.
- **Accountability** -- From wrongful arrests to fabricated court citations, the pattern is identical: AI makes a confident decision, humans accept it without verification, someone gets hurt. Glass makes the AI's process visible enough that verification is possible -- not just theoretically, but in the normal flow of using the tool. The seal makes this verification auditable by third parties.
- **Provenance in the age of AI authorship** -- The Claude Code leak revealed AI instructed to hide its identity. HN discussions now routinely debate whether code, text, and even legal filings were AI-generated. Glass does not hide. It signs. Every response carries a verifiable chain proving exactly what process produced it.
- **Agent observability** -- Multi-agent systems are becoming standard. Developers already build "separation of powers" architectures with builder, reviewer, and tester agents. Glass provides the observability layer: what did each step actually do, and does the ground truth match the agent's summary?
- **Portable proof for a post-trust world** -- When LiteLLM is poisoned for 40 minutes and hits hundreds of thousands of machines, when courts publish AI-hallucinated citations, when police arrest innocent people based on AI matches nobody can audit -- the demand is not just "show me what happened" but "give me proof I can take to someone who wasn't there." Exportable proof bundles make Glass's audit trail a first-class document: downloadable, shareable, archivable, and independently verifiable without Glass running.

The first system that makes AI operations watchable in real time -- with cryptographic proof that the record is unaltered and exportable proof that anyone can verify -- does not just build a better chatbot. It establishes the norm that AI systems must be observable, provably honest, and accountable to third parties.

### The Compliance Pivot: From Cultural Statement to Market Entry

After 13 persona reviews across 4 feedback rounds, the primary user has been refined from "developers" to **compliance teams at AI-using companies** -- VPs of Compliance, GRC analysts, legal teams. The willingness to pay is high ($20K-100K/year for compliant tooling), and the market timing is urgent: EU AI Act Article 12 (record-keeping for high-risk AI) begins full enforcement in August 2026, four months away.

This does not mean Glass abandons its cultural origins. It means the *same architecture* -- process visibility, tamper-evident audit trails, portable proof bundles -- now has a buyer who needs it for regulatory survival, not just philosophical conviction.

Key features for the compliance market:
- **PDF proof bundles** with header, signature block, control references, and EU AI Act Article 12 framing
- **Structured JSON logging** with request IDs for log aggregator ingestion
- **Health/readiness probe split** (/healthz + /readyz) for production deployment
- **Plain-language landing page** written for compliance buyers, not developers

The contrarian's challenge remains valid: Glass proves "we did what we said we did" but cannot prove "what we did was right." The self-attestation disclosure is embedded in every proof bundle -- PDF and JSON -- and prominently displayed on every landing page. Owning this ceiling explicitly makes the product defensible. Hiding it would invite a takedown.

### The Calibration Turn: Measuring the Ceiling

The contrarian's hardest question -- "what fraction of Consistent claims are actually true?" -- cannot be answered by architecture alone. It requires tedious empirical work: humans judging whether individual claims Glass labeled "consistent" turned out to be correct in the real world.

Glass v0.6 answers this directly with a **calibration system**. Human reviewers submit ground-truth judgments for past claims. The system computes:
- **Per-status accuracy**: of all claims Glass labeled "consistent", what fraction were actually correct?
- **Calibration gap**: the difference between the implied accuracy (100% for "consistent") and the observed accuracy. A gap of 0.3 means 30% of "consistent" claims were wrong.
- **Sample size sufficiency**: whether enough judgments exist (>= 30 per status) for statistical significance.

This moves Glass from "receipts without guarantees" to "receipts with empirical measurement." The calibration gap is the project's honesty metric -- exposed via API, never hidden. When the gap is large, Glass is being honest about its dishonesty. When it shrinks over time (through better models, tighter prompts, or domain-specific tuning), that improvement is measurable.

The HN signal is clear: the Zero-Error Horizon paper (April 2026) argues that "know your model's error-free envelope, not just its mean score." Calibration is Glass's answer to this for LLM transparency -- not benchmarks, not averages, but the empirical fraction of correct claims per confidence label.

### The Streaming Turn: Ground Truth in Real Time

The HN community's "dangerously sanitized optimism" finding -- that agents lie about their own progress -- has a subtle implication for Glass itself. The previous Glass UI used `setTimeout` timers to animate pipeline stages, showing fake progress while the server processed the query. This is exactly the kind of process simulation that Glass exists to eliminate.

Glass v0.6 replaces this with **Server-Sent Events (SSE)**. The `/api/query/stream` endpoint emits real events as each pipeline stage completes on the server. The frontend renders these events as they arrive -- no timers, no simulation, no fake animation. Every stage indicator in the UI reflects actual server-side completion.

A transparency tool that simulates its own transparency is a contradiction. The SSE pipeline is the fix.
