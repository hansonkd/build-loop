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

    return True, f"Seal intact: {len(events)} events, chain consistent"


def content_hash(text: str) -> str:
    """Return the full SHA-256 hash of text content for audit purposes.

    Previously truncated to 16 hex chars (64-bit), which is in birthday-attack
    territory. Now returns the full 64 hex chars (256-bit) for proper collision
    resistance.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


SELF_ATTESTATION_DISCLOSURE = (
    "This seal proves the audit trail has not been modified after it was written. "
    "It does NOT prove the trail was accurate when written. Glass generates its own "
    "audit trail — the seal is self-attestation, not independent verification. "
    "The consistency checks use the same type of LLM that generated the response, "
    "so 'consistent' means internally coherent, not factually correct."
)

VERIFICATION_INSTRUCTIONS = """To verify this proof bundle independently:

1. Start with prev_hash = "genesis"
2. For each event in the audit_trail array, in order:
   a. Build a canonical string: "{timestamp}|{operation}|{description}|{backend}|{latency_ms}|{bytes_sent}|{bytes_received}|{destination}|{content_hash}"
   b. Compute event_digest = SHA-256(canonical_string) as a hex string
   c. Compute expected_chain_hash = SHA-256("{prev_hash}:{event_digest}") as a hex string
   d. Compare expected_chain_hash to the event's chain_hash field. If they differ, the chain is broken.
   e. Set prev_hash = event's chain_hash
3. After processing all events, the last event's chain_hash should equal the provenance_seal field.
4. If all checks pass, the audit trail is intact and has not been tampered with.

IMPORTANT — what this proves and does not prove:
""" + SELF_ATTESTATION_DISCLOSURE + """

This verification requires only SHA-256 (available in any programming language) and no trust in Glass."""

GLASS_VERSION = "0.7.0"


def build_proof_bundle(response) -> dict:
    """Build a self-contained, portable proof bundle from a GlassResponse.

    The bundle contains everything needed to independently verify that
    the audit trail has not been tampered with. No Glass installation,
    no API key, no trust required -- just SHA-256.
    """
    from datetime import datetime, timezone

    return {
        "proof_bundle_version": "1.1",
        "glass_version": GLASS_VERSION,
        "bundle_generated_at": datetime.now(timezone.utc).isoformat(),
        "self_attestation_disclosure": SELF_ATTESTATION_DISCLOSURE,
        "verification_instructions": VERIFICATION_INSTRUCTIONS.strip(),
        "response": {
            "id": response.id,
            "query": response.query,
            "raw_response": response.raw_response,
            "reasoning_trace": response.reasoning_trace,
            "claims": [c.model_dump() for c in response.claims],
            "premise_flags": response.premise_flags,
            "backend": response.backend,
            "verifier_backend": getattr(response, "verifier_backend", None),
            "timestamp": response.timestamp,
        },
        "compliance": response.compliance.model_dump() if hasattr(response, "compliance") else {},
        "audit_trail": [e.model_dump() for e in response.audit_trail],
        "provenance_seal": response.provenance_seal,
        "seal_verification": {
            "algorithm": "SHA-256 hash chain",
            "genesis_value": "genesis",
            "chain_length": len(response.audit_trail),
            "canonical_format": "{timestamp}|{operation}|{description}|{backend}|{latency_ms}|{bytes_sent}|{bytes_received}|{destination}|{content_hash}",
            "link_format": "SHA-256({prev_chain_hash}:{event_digest})",
        },
    }


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
