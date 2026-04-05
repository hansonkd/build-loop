import json
import re

import httpx

from glass.audit import AuditTrail, AuditedTimer, content_hash
from glass.config import Settings
from glass.models import Claim

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
    raw = await _call_llm(prompt, backend, settings, trail, "Decompose response into claims")
    return _parse_claims(raw, text)


async def check_premises(query: str, backend: str, settings: Settings, trail: AuditTrail) -> list[str]:
    prompt = PREMISE_CHECK_PROMPT.format(query=query)
    raw = await _call_llm(prompt, backend, settings, trail, "Check query premises for errors")
    try:
        result = json.loads(_extract_json(raw))
        if isinstance(result, list):
            return [str(item) for item in result]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


async def _call_llm(prompt: str, backend: str, settings: Settings, trail: AuditTrail, description: str) -> str:
    prompt_bytes = len(prompt.encode())

    if backend == "ollama":
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        with AuditedTimer() as timer:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                text = resp.json()["response"]
        trail.record(
            operation="llm_call",
            description=f"{description} via ollama ({settings.ollama_model})",
            backend="ollama",
            latency_ms=timer.elapsed_ms,
            bytes_sent=prompt_bytes,
            bytes_received=len(text.encode()),
            destination=f"local/ollama ({settings.ollama_base_url})",
            content_hash=content_hash(text),
        )
        return text

    elif backend == "openrouter":
        payload = {
            "model": settings.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
        }
        payload_bytes = len(json.dumps(payload).encode())
        with AuditedTimer() as timer:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openrouter_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"]
        trail.record(
            operation="llm_call",
            description=f"{description} via openrouter ({settings.openrouter_model})",
            backend="openrouter",
            latency_ms=timer.elapsed_ms,
            bytes_sent=payload_bytes,
            bytes_received=len(text.encode()),
            destination="openrouter.ai",
            content_hash=content_hash(text),
        )
        return text

    elif backend == "claude":
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        with AuditedTimer() as timer:
            message = await client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text
        trail.record(
            operation="llm_call",
            description=f"{description} via claude ({settings.claude_model})",
            backend="claude",
            latency_ms=timer.elapsed_ms,
            bytes_sent=prompt_bytes,
            bytes_received=len(text.encode()),
            destination="api.anthropic.com",
            content_hash=content_hash(text),
        )
        return text

    else:
        raise ValueError(f"Unknown backend: {backend}")


def _extract_json(text: str) -> str:
    """Extract JSON array from text that might contain markdown fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?])\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"(\[.*])", text, re.DOTALL)
    if match:
        return match.group(1)
    return text


def _parse_claims(raw: str, original_text: str) -> list[Claim]:
    try:
        items = json.loads(_extract_json(raw))
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
                evidence="Not yet verified",
                source_span=span,
            )
        )
    return claims
