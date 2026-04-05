import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from glass.audit import AuditTrail, AuditedTimer, build_proof_bundle, content_hash, verify_seal
from glass.config import Settings
from glass.db import (
    delete_memory,
    get_audit_trail,
    get_response,
    init_db,
    list_memory,
    list_responses,
    save_response,
)
from glass.decomposer import check_premises, decompose_claims
from glass.generator import detect_backend, generate
from glass.models import AuditEvent, GlassResponse, QueryRequest, StatusResponse
from glass.verifier import verify_claims

logger = logging.getLogger(__name__)

settings = Settings.from_env()

# Cached backend — detected once at startup, refreshed via /api/status if needed
_cached_backend: str | None = None
_backend_detected: bool = False


async def _get_backend() -> str | None:
    """Return cached backend, detecting on first call."""
    global _cached_backend, _backend_detected
    if not _backend_detected:
        _cached_backend = await detect_backend(settings)
        _backend_detected = True
    return _cached_backend


async def _refresh_backend() -> str | None:
    """Force re-detection of backend (e.g., if Ollama was started after Glass)."""
    global _cached_backend, _backend_detected
    _cached_backend = await detect_backend(settings)
    _backend_detected = True
    return _cached_backend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    init_db(settings.db_path)
    # Detect backend once at startup instead of probing on every request
    await _get_backend()
    logger.info("Glass started — backend: %s", _cached_backend or "none")
    yield


app = FastAPI(title="Glass", description="AI that shows its work — all of it", lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/status")
async def status() -> StatusResponse:
    # Refresh on status check so users can start Ollama and see it picked up
    backend = await _refresh_backend()
    if backend is None:
        return StatusResponse(
            backend=None,
            model=None,
            message="No LLM backend available. Install Ollama or set OPENROUTER_API_KEY or ANTHROPIC_API_KEY.",
        )
    model_map = {"ollama": settings.ollama_model, "openrouter": settings.openrouter_model, "claude": settings.claude_model}
    model = model_map.get(backend, "unknown")
    return StatusResponse(backend=backend, model=model, message=f"Using {backend} ({model})")


@app.post("/api/query")
async def query(req: QueryRequest) -> GlassResponse:
    backend = await _get_backend()
    if backend is None:
        raise HTTPException(
            status_code=503,
            detail="No model backend is available. Install Ollama or set ANTHROPIC_API_KEY.",
        )

    trail = AuditTrail()

    # Generate response with reasoning trace — record failure if it happens
    try:
        raw_response, reasoning_trace = await generate(req.query, backend, settings, trail)
    except Exception as exc:
        logger.error("Generation failed: %s", exc)
        trail.record(
            operation="llm_call",
            description=f"Generate response — FAILED: {type(exc).__name__}: {exc}",
            backend=backend,
            latency_ms=0,
            bytes_sent=len(req.query.encode()),
            bytes_received=0,
            destination="error",
        )
        raise HTTPException(
            status_code=502,
            detail=f"LLM generation failed: {exc}",
        )

    # Check user's premises for errors
    premise_flags = await check_premises(req.query, backend, settings, trail)

    # Decompose into claims
    claims = await decompose_claims(raw_response, backend, settings, trail)

    # Check each claim for consistency
    claims = await verify_claims(claims, reasoning_trace, backend, settings, trail)

    response = GlassResponse(
        id=str(uuid.uuid4()),
        query=req.query,
        raw_response=raw_response,
        reasoning_trace=reasoning_trace,
        claims=claims,
        premise_flags=premise_flags,
        audit_trail=trail.to_list(),
        provenance_seal="",
        backend=backend,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Record the DB write in the audit trail before saving
    with AuditedTimer() as timer:
        save_response(settings.db_path, response)
    trail.record(
        operation="db_write",
        description="Save response to local SQLite database",
        backend=None,
        latency_ms=timer.elapsed_ms,
        bytes_sent=0,
        bytes_received=0,
        destination="local/sqlite",
        content_hash=content_hash(response.id),
    )

    # Compute provenance seal and update the response
    response.audit_trail = trail.to_list()
    response.provenance_seal = trail.seal()

    # Re-save with the final seal included
    save_response(settings.db_path, response, upsert=True)

    return response


@app.get("/api/history")
async def history(limit: int = 50, offset: int = 0):
    return list_responses(settings.db_path, limit=limit, offset=offset)


@app.get("/api/response/{response_id}")
async def get_single_response(response_id: str):
    resp = get_response(settings.db_path, response_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Response not found")
    return resp


@app.get("/api/response/{response_id}/audit")
async def get_response_audit(response_id: str):
    trail = get_audit_trail(settings.db_path, response_id)
    if trail is None:
        raise HTTPException(status_code=404, detail="Response not found")
    return trail


@app.get("/api/response/{response_id}/verify")
async def verify_response_provenance(response_id: str):
    """Recompute the provenance chain and check that the seal is intact.

    This is a pure local computation — no trust in Glass required.
    Anyone can independently verify by recomputing the SHA-256 chain.
    """
    resp = get_response(settings.db_path, response_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Response not found")

    is_valid, message = verify_seal(resp.audit_trail)

    # Also check that the recomputed seal matches the stored one
    if is_valid and resp.audit_trail:
        recomputed = resp.audit_trail[-1].chain_hash
        if resp.provenance_seal and resp.provenance_seal != recomputed:
            is_valid = False
            message = f"Stored seal does not match recomputed chain. Stored: {resp.provenance_seal[:32]}..., Computed: {recomputed[:32]}..."

    return {
        "response_id": response_id,
        "seal": resp.provenance_seal,
        "chain_intact": is_valid,
        "message": message,
        "events_checked": len(resp.audit_trail),
    }


@app.get("/api/response/{response_id}/bundle")
async def export_proof_bundle(response_id: str):
    """Export a self-contained proof bundle for independent verification.

    The bundle is a JSON document containing everything needed to verify
    that the audit trail has not been tampered with. No Glass installation,
    no API key, no trust required -- just SHA-256.
    """
    resp = get_response(settings.db_path, response_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Response not found")

    bundle = build_proof_bundle(resp)

    # Verify the seal inline so the bundle includes verification status
    is_valid, message = verify_seal(resp.audit_trail)
    if is_valid and resp.audit_trail:
        recomputed = resp.audit_trail[-1].chain_hash
        if resp.provenance_seal and resp.provenance_seal != recomputed:
            is_valid = False
            message = f"Stored seal does not match recomputed chain"

    bundle["seal_status"] = {
        "chain_intact": is_valid,
        "message": message,
        "events_checked": len(resp.audit_trail),
    }

    return bundle


@app.get("/api/memory")
async def memory_list():
    return list_memory(settings.db_path)


@app.delete("/api/memory/{memory_id}")
async def memory_delete(memory_id: str):
    if not delete_memory(settings.db_path, memory_id):
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"status": "deleted"}


def cli():
    import uvicorn

    uvicorn.run(
        "glass.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    cli()
