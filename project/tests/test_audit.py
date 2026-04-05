"""Tests for audit trail: seal creation, verification, and tamper detection."""

from glass.audit import AuditTrail, content_hash, verify_seal


def test_verify_seal():
    """Build a trail with multiple events, seal it, verify returns True."""
    trail = AuditTrail()
    trail.record(
        operation="llm_call",
        description="Generate response via ollama (llama3.2)",
        backend="ollama",
        latency_ms=120,
        bytes_sent=500,
        bytes_received=1200,
        destination="local/ollama (http://localhost:11434)",
        content_hash="a" * 64,
    )
    trail.record(
        operation="llm_call",
        description="Decompose response into claims via ollama (llama3.2)",
        backend="ollama",
        latency_ms=80,
        bytes_sent=300,
        bytes_received=600,
        destination="local/ollama (http://localhost:11434)",
        content_hash="b" * 64,
    )
    trail.record(
        operation="db_write",
        description="Save response to local SQLite database",
        backend=None,
        latency_ms=5,
        bytes_sent=0,
        bytes_received=0,
        destination="local/sqlite",
        content_hash="c" * 64,
    )

    seal = trail.seal()
    assert seal != "empty"
    assert len(seal) == 64  # full SHA-256 hex

    is_valid, message = verify_seal(trail.to_list())
    assert is_valid is True
    assert "intact" in message.lower()


def test_verify_seal_tampered():
    """Build a trail, mutate a field in the middle, verify returns False."""
    trail = AuditTrail()
    trail.record(
        operation="llm_call",
        description="Generate response",
        backend="ollama",
        latency_ms=100,
        bytes_sent=400,
        bytes_received=800,
        destination="local/ollama",
        content_hash="d" * 64,
    )
    trail.record(
        operation="llm_call",
        description="Check claims",
        backend="ollama",
        latency_ms=90,
        bytes_sent=300,
        bytes_received=700,
        destination="local/ollama",
        content_hash="e" * 64,
    )

    events = trail.to_list()
    # Tamper with the first event's description after sealing
    events[0].description = "TAMPERED — this was not the original description"

    is_valid, message = verify_seal(events)
    assert is_valid is False
    assert "broken" in message.lower()


def test_verify_seal_empty():
    """Verify that an empty trail is considered valid."""
    is_valid, message = verify_seal([])
    assert is_valid is True


def test_content_hash():
    """Verify content_hash returns full 64-char SHA-256 hex string."""
    h = content_hash("hello world")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    # SHA-256 of "hello world" is a known value
    assert h == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_content_hash_deterministic():
    """Same input always produces the same hash."""
    assert content_hash("test input") == content_hash("test input")


def test_content_hash_different_inputs():
    """Different inputs produce different hashes."""
    assert content_hash("input A") != content_hash("input B")
