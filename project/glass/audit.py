"""Audit trail — captures every operation Glass performs during a query lifecycle.

Every LLM call, network request, and storage operation is logged with timing,
payload sizes, and content hashes. The trail is stored locally and never sent
to external services.

Provenance seals: each event is chained to the previous via SHA-256, forming
a hash chain. The final hash (the "seal") proves the trail is unaltered.
Anyone can verify by recomputing the chain — no trust in Glass required.
"""

import hashlib
import time
from dataclasses import dataclass, field

from glass.models import AuditEvent


def _event_digest(event: AuditEvent) -> str:
    """Compute a canonical digest of an event's content (excluding chain_hash)."""
    canonical = f"{event.timestamp}|{event.operation}|{event.description}|{event.backend}|{event.latency_ms}|{event.bytes_sent}|{event.bytes_received}|{event.destination}|{event.content_hash}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _chain_link(event_digest: str, prev_chain_hash: str) -> str:
    """Compute the chain hash for an event given the previous chain hash."""
    link = f"{prev_chain_hash}:{event_digest}"
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


@dataclass
class AuditTrail:
    """Collects audit events during a single request lifecycle."""

    events: list[AuditEvent] = field(default_factory=list)

    def record(
        self,
        operation: str,
        description: str,
        backend: str | None = None,
        latency_ms: int = 0,
        bytes_sent: int = 0,
        bytes_received: int = 0,
        destination: str = "local",
        content_hash: str = "",
    ) -> None:
        from datetime import datetime, timezone

        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            description=description,
            backend=backend,
            latency_ms=latency_ms,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            destination=destination,
            content_hash=content_hash,
        )

        # Compute provenance chain hash
        prev_hash = self.events[-1].chain_hash if self.events else "genesis"
        digest = _event_digest(event)
        event.chain_hash = _chain_link(digest, prev_hash)

        self.events.append(event)

    def to_list(self) -> list[AuditEvent]:
        return list(self.events)

    def seal(self) -> str:
        """Return the provenance seal — the chain_hash of the last event.

        If there are no events, returns 'empty'. The seal can be verified
        by recomputing the chain from the event list.
        """
        if not self.events:
            return "empty"
        return self.events[-1].chain_hash


def verify_seal(events: list[AuditEvent]) -> tuple[bool, str]:
    """Verify that a provenance chain is intact.

    Returns (is_valid, message). Recomputes every chain_hash from scratch
    and checks it matches the stored value. No trust required — pure math.
    """
    if not events:
        return True, "No events to verify"

    prev_hash = "genesis"
    for i, event in enumerate(events):
        digest = _event_digest(event)
        expected = _chain_link(digest, prev_hash)
        if event.chain_hash != expected:
            return False, f"Chain broken at event {i}: '{event.description}'. Expected {expected[:16]}..., got {event.chain_hash[:16]}..."
        prev_hash = event.chain_hash

    return True, f"Seal verified: {len(events)} events, chain intact"


def content_hash(text: str) -> str:
    """Return a truncated SHA-256 hash of text content for audit purposes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class AuditedTimer:
    """Context manager that measures elapsed time for an operation."""

    def __init__(self):
        self.start_time: float = 0
        self.elapsed_ms: int = 0

    def __enter__(self):
        self.start_time = time.monotonic()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.monotonic() - self.start_time) * 1000)
