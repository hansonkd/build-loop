from __future__ import annotations

import json
import logging

import httpx

from glass.audit import AuditTrail
from glass.config import Settings
from glass.llm_client import call_llm, extract_json
from glass.models import Claim

logger = logging.getLogger(__name__)

VERIFY_PROMPT = """You are a claim consistency checker. Your job is to assess whether individual claims extracted from an AI response are internally consistent with the reasoning that produced them.

IMPORTANT: You are checking self-consistency, not factual accuracy. You are the same type of model that generated the response. Your assessment reflects internal coherence, not external ground truth.

For each claim, determine:
1. **Self-consistency**: Does it contradict any other claims in the set?
2. **Reasoning support**: Is it supported by the reasoning trace provided?
3. **Confidence level**: How definitive vs. hedged is the assertion?

Assign each claim one of these statuses:
- "consistent": The claim is internally consistent with the reasoning and other claims, stated with appropriate confidence
- "uncertain": The claim is plausible but either weakly supported, potentially contradicted, or stated more confidently than warranted
- "unverifiable": The claim cannot be assessed from the available information (e.g., requires external data not in the reasoning)

Return a JSON array where each element has:
- "index": the claim index (0-based)
- "status": "consistent" | "uncertain" | "unverifiable"
- "evidence": a short sentence explaining why you assigned this status

Respond with ONLY the JSON array, no other text.

Reasoning trace:
---
{reasoning}
---

Claims to check:
---
{claims}
---"""


async def verify_claims(
    claims: list[Claim], reasoning_trace: str, backend: str, settings: Settings, trail: AuditTrail, http_client: httpx.AsyncClient | None = None, anthropic_client=None,
) -> list[Claim]:
    if not claims:
        return claims

    claims_text = "\n".join(f"{i}. {c.text}" for i, c in enumerate(claims))
    prompt = VERIFY_PROMPT.format(reasoning=reasoning_trace, claims=claims_text)

    try:
        raw = await call_llm(prompt, backend, settings, trail, "Check claim consistency", http_client=http_client, anthropic_client=anthropic_client)
    except Exception as exc:
        logger.error("LLM call failed during claim verification: %s", exc)
        trail.record(
            operation="llm_call",
            description=f"Check claim consistency — FAILED: {type(exc).__name__}: {exc}",
            backend=backend,
            latency_ms=0,
            bytes_sent=len(prompt.encode()),
            bytes_received=0,
            destination="error",
        )
        return claims  # return with default "unverifiable" status

    try:
        verdicts = json.loads(extract_json(raw))
    except (json.JSONDecodeError, ValueError):
        return claims  # return with default "unverifiable" status

    verdict_map = {}
    for v in verdicts:
        if isinstance(v, dict) and "index" in v:
            verdict_map[v["index"]] = v

    checked_claims = []
    for i, claim in enumerate(claims):
        if i in verdict_map:
            v = verdict_map[i]
            status = v.get("status", "unverifiable")
            # Accept both old "verified" responses from LLM and new "consistent"
            if status == "verified":
                status = "consistent"
            if status not in ("consistent", "uncertain", "unverifiable"):
                status = "unverifiable"
            checked_claims.append(
                Claim(
                    text=claim.text,
                    status=status,
                    evidence=v.get("evidence", "No evidence provided"),
                    source_span=claim.source_span,
                )
            )
        else:
            checked_claims.append(claim)

    return checked_claims
