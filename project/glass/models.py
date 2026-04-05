from typing import Literal

from pydantic import BaseModel


class Claim(BaseModel):
    text: str
    status: Literal["consistent", "uncertain", "unverifiable"]
    evidence: str
    source_span: list[int]  # [start, end] character offsets


class AuditEvent(BaseModel):
    timestamp: str
    operation: str  # "llm_call" | "network_request" | "db_write"
    description: str  # Human-readable (e.g., "Generate response via openrouter")
    backend: str | None  # Which backend was used
    latency_ms: int  # How long the operation took
    bytes_sent: int  # Payload size sent
    bytes_received: int  # Payload size received
    destination: str  # Where data went (e.g., "openrouter.ai", "local/ollama", "local/sqlite")
    content_hash: str  # Truncated SHA-256 of response content
    chain_hash: str = ""  # Provenance chain: hash of this event + previous chain_hash


class QueryRequest(BaseModel):
    query: str


class GlassResponse(BaseModel):
    id: str
    query: str
    raw_response: str
    reasoning_trace: str
    claims: list[Claim]
    premise_flags: list[str]
    audit_trail: list[AuditEvent]
    provenance_seal: str = ""  # Hash chain head — proves audit trail is unaltered
    backend: str  # "ollama" | "openrouter" | "claude"
    timestamp: str


class MemoryEntry(BaseModel):
    id: str
    key: str
    value: str
    source_response_id: str
    created_at: str
    last_accessed: str
    access_count: int


class StatusResponse(BaseModel):
    backend: str | None
    model: str | None
    message: str
