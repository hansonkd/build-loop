"""Shared LLM client — single implementation of _call_llm and _extract_json.

Extracted from decomposer.py and verifier.py to eliminate ~85 lines of
duplication. Every LLM call in the pipeline goes through this module.
"""

import json
import logging
import re

import httpx

from glass.audit import AuditTrail, AuditedTimer, content_hash
from glass.config import Settings

logger = logging.getLogger(__name__)


async def call_llm(
    prompt: str,
    backend: str,
    settings: Settings,
    trail: AuditTrail,
    description: str,
) -> str:
    """Send a prompt to the configured LLM backend and record it in the audit trail.

    Raises on network/API errors — callers are responsible for handling failures
    and recording them in the audit trail if desired.
    """
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


def extract_json(text: str) -> str:
    """Extract a JSON array from text that might contain markdown fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(\[.*?])\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    match = re.search(r"(\[.*])", text, re.DOTALL)
    if match:
        return match.group(1)
    return text
