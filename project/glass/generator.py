from __future__ import annotations

import json

import httpx

from glass.audit import AuditTrail, AuditedTimer, content_hash
from glass.config import Settings

SYSTEM_PROMPT = """You are Glass, an AI assistant that prioritizes honesty and transparency over impressiveness.

Rules:
- Think step-by-step. Show your reasoning explicitly.
- When you are uncertain, say so clearly. Use phrases like "I'm not sure about this" or "I don't know".
- Never fabricate information to appear more helpful.
- If the user's question contains a false premise, identify it before answering.
- Prefer a partial, accurate answer over a complete, speculative one.
- Never use filler phrases like "Great question!" — respond to content, not to the user's ego.
- If you disagree with the user, say so and explain why.

Format your response in two sections:
<reasoning>
Your step-by-step thinking process. Include doubts, alternatives considered, and what you're uncertain about.
</reasoning>

<answer>
Your final answer to the user. Be direct and concise.
</answer>"""


async def check_ollama(settings: Settings, http_client: httpx.AsyncClient | None = None) -> bool:
    try:
        if http_client is not None:
            resp = await http_client.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
            return resp.status_code == 200
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _check_openrouter_available(settings: Settings) -> bool:
    return settings.openrouter_api_key is not None


def _check_claude_available(settings: Settings) -> bool:
    return settings.anthropic_api_key is not None


async def detect_backend(settings: Settings, http_client: httpx.AsyncClient | None = None) -> str | None:
    if await check_ollama(settings, http_client):
        return "ollama"
    if _check_openrouter_available(settings):
        return "openrouter"
    if _check_claude_available(settings):
        return "claude"
    return None


async def generate_ollama(query: str, settings: Settings, trail: AuditTrail, http_client: httpx.AsyncClient | None = None) -> tuple[str, str]:
    """Returns (raw_response, reasoning_trace)."""
    payload = {
        "model": settings.ollama_model,
        "prompt": query,
        "system": SYSTEM_PROMPT,
        "stream": False,
    }
    payload_str = str(payload)
    with AuditedTimer() as timer:
        if http_client is not None:
            resp = await http_client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
        else:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json=payload,
                )
        resp.raise_for_status()
        text = resp.json()["response"]
    trail.record(
        operation="llm_call",
        description=f"Generate response via ollama ({settings.ollama_model})",
        backend="ollama",
        latency_ms=timer.elapsed_ms,
        bytes_sent=len(payload_str.encode()),
        bytes_received=len(text.encode()),
        destination=f"local/ollama ({settings.ollama_base_url})",
        content_hash=content_hash(text),
    )
    return _parse_sections(text)


async def generate_claude(query: str, settings: Settings, trail: AuditTrail, anthropic_client=None) -> tuple[str, str]:
    """Returns (raw_response, reasoning_trace)."""
    import anthropic

    client = anthropic_client or anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt_bytes = len(query.encode()) + len(SYSTEM_PROMPT.encode())
    with AuditedTimer() as timer:
        message = await client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": query}],
        )
        text = message.content[0].text
    trail.record(
        operation="llm_call",
        description=f"Generate response via claude ({settings.claude_model})",
        backend="claude",
        latency_ms=timer.elapsed_ms,
        bytes_sent=prompt_bytes,
        bytes_received=len(text.encode()),
        destination="api.anthropic.com",
        content_hash=content_hash(text),
    )
    return _parse_sections(text)


async def generate_openrouter(query: str, settings: Settings, trail: AuditTrail, http_client: httpx.AsyncClient | None = None) -> tuple[str, str]:
    """Returns (raw_response, reasoning_trace)."""
    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "max_tokens": 4096,
    }
    payload_bytes = len(json.dumps(payload).encode())
    with AuditedTimer() as timer:
        if http_client is not None:
            resp = await http_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        else:
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
        description=f"Generate response via openrouter ({settings.openrouter_model})",
        backend="openrouter",
        latency_ms=timer.elapsed_ms,
        bytes_sent=payload_bytes,
        bytes_received=len(text.encode()),
        destination="openrouter.ai",
        content_hash=content_hash(text),
    )
    return _parse_sections(text)


async def generate(query: str, backend: str, settings: Settings, trail: AuditTrail, http_client: httpx.AsyncClient | None = None, anthropic_client=None) -> tuple[str, str]:
    if backend == "ollama":
        return await generate_ollama(query, settings, trail, http_client=http_client)
    elif backend == "openrouter":
        return await generate_openrouter(query, settings, trail, http_client=http_client)
    elif backend == "claude":
        return await generate_claude(query, settings, trail, anthropic_client=anthropic_client)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _parse_sections(text: str) -> tuple[str, str]:
    """Parse <reasoning> and <answer> sections. Returns (answer, reasoning)."""
    reasoning = ""
    answer = text

    if "<reasoning>" in text and "</reasoning>" in text:
        start = text.index("<reasoning>") + len("<reasoning>")
        end = text.index("</reasoning>")
        reasoning = text[start:end].strip()

    if "<answer>" in text and "</answer>" in text:
        start = text.index("<answer>") + len("<answer>")
        end = text.index("</answer>")
        answer = text[start:end].strip()
    elif "<answer>" in text:
        start = text.index("<answer>") + len("<answer>")
        answer = text[start:].strip()

    return answer, reasoning
