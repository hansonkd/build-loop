import json
import re

import httpx

from glass.audit import AuditTrail, AuditedTimer, content_hash
from glass.config import Settings
from glass.models import Claim

VERIFY_PROMPT = """You are a claim verifier. Your job is to assess the reliability of individual claims extracted from an AI response.

For each claim, determine:
1. **Self-consistency**: Does it contradict any other claims in the set?
2. **Reasoning support**: Is it supported by the reasoning trace provided?
3. **Confidence level**: How definitive vs. hedged is the assertion?

Assign each claim one of these statuses:
- "verified": The claim is internally consistent, supported by the reasoning, and stated with appropriate confidence
- "uncertain": The claim is plausible but either weakly supported, potentially contradicted, or stated more confidently than warranted
- "unverifiable": The claim cannot be assessed from the available information (e.g., requires external data not in the reasoning)

Return a JSON array where each element has:
- "index": the claim index (0-based)
- "status": "verified" | "uncertain" | "unverifiable"
- "evidence": a short sentence explaining why you assigned this status

Respond with ONLY the JSON array, no other text.

Reasoning trace:
---
{reasoning}
---

Claims to verify:
---
{claims}
---"""


async def verify_claims(
    claims: list[Claim], reasoning_trace: str, backend: str, settings: Settings, trail: AuditTrail
) -> list[Claim]:
    if not claims:
        return claims

    claims_text = "\n".join(f"{i}. {c.text}" for i, c in enumerate(claims))
    prompt = VERIFY_PROMPT.format(reasoning=reasoning_trace, claims=claims_text)
    raw = await _call_llm(prompt, backend, settings, trail)

    try:
        verdicts = json.loads(_extract_json(raw))
    except (json.JSONDecodeError, ValueError):
        return claims  # return with default "unverifiable" status

    verdict_map = {}
    for v in verdicts:
        if isinstance(v, dict) and "index" in v:
            verdict_map[v["index"]] = v

    verified_claims = []
    for i, claim in enumerate(claims):
        if i in verdict_map:
            v = verdict_map[i]
            status = v.get("status", "unverifiable")
            if status not in ("verified", "uncertain", "unverifiable"):
                status = "unverifiable"
            verified_claims.append(
                Claim(
                    text=claim.text,
                    status=status,
                    evidence=v.get("evidence", "No evidence provided"),
                    source_span=claim.source_span,
                )
            )
        else:
            verified_claims.append(claim)

    return verified_claims


async def _call_llm(prompt: str, backend: str, settings: Settings, trail: AuditTrail) -> str:
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
            description=f"Verify claims via ollama ({settings.ollama_model})",
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
            description=f"Verify claims via openrouter ({settings.openrouter_model})",
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
            description=f"Verify claims via claude ({settings.claude_model})",
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
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?])\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"(\[.*])", text, re.DOTALL)
    if match:
        return match.group(1)
    return text
