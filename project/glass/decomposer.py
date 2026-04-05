import json
import logging

from glass.audit import AuditTrail
from glass.config import Settings
from glass.llm_client import call_llm, extract_json
from glass.models import Claim

logger = logging.getLogger(__name__)

DECOMPOSE_PROMPT = """Extract individual factual claims from the following text. Each claim should be a single, atomic assertion that can be independently verified.

Return a JSON array where each element has:
- "text": the claim as a standalone sentence
- "source_span": [start_index, end_index] approximate character offsets in the original text

Only extract factual claims. Skip opinions, hedges, and meta-statements like "I think" or "Let me explain".

If the text contains no verifiable claims, return an empty array.

Respond with ONLY the JSON array, no other text.

Text to decompose:
---
{text}
---"""

PREMISE_CHECK_PROMPT = """Analyze the following user query for false premises, incorrect assumptions, or factual errors embedded in the question itself.

If the query contains problematic premises, list each one as a short sentence.
If the query is fine, return an empty array.

Respond with ONLY a JSON array of strings, no other text.

Query:
---
{query}
---"""


async def decompose_claims(text: str, backend: str, settings: Settings, trail: AuditTrail) -> list[Claim]:
    prompt = DECOMPOSE_PROMPT.format(text=text)
    try:
        raw = await call_llm(prompt, backend, settings, trail, "Decompose response into claims")
    except Exception as exc:
        logger.error("LLM call failed during decomposition: %s", exc)
        trail.record(
            operation="llm_call",
            description=f"Decompose response into claims — FAILED: {type(exc).__name__}: {exc}",
            backend=backend,
            latency_ms=0,
            bytes_sent=len(prompt.encode()),
            bytes_received=0,
            destination="error",
        )
        return []
    return _parse_claims(raw, text)


async def check_premises(query: str, backend: str, settings: Settings, trail: AuditTrail) -> list[str]:
    prompt = PREMISE_CHECK_PROMPT.format(query=query)
    try:
        raw = await call_llm(prompt, backend, settings, trail, "Check query premises for errors")
    except Exception as exc:
        logger.error("LLM call failed during premise check: %s", exc)
        trail.record(
            operation="llm_call",
            description=f"Check query premises — FAILED: {type(exc).__name__}: {exc}",
            backend=backend,
            latency_ms=0,
            bytes_sent=len(prompt.encode()),
            bytes_received=0,
            destination="error",
        )
        return []
    try:
        result = json.loads(extract_json(raw))
        if isinstance(result, list):
            return [str(item) for item in result]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def _parse_claims(raw: str, original_text: str) -> list[Claim]:
    try:
        items = json.loads(extract_json(raw))
    except (json.JSONDecodeError, ValueError):
        return []

    claims = []
    for item in items:
        if not isinstance(item, dict) or "text" not in item:
            continue
        span = item.get("source_span", [0, 0])
        if not isinstance(span, list) or len(span) != 2:
            span = [0, len(original_text)]
        claims.append(
            Claim(
                text=item["text"],
                status="unverifiable",  # default, verifier will update
                evidence="Not yet assessed",
                source_span=span,
            )
        )
    return claims
