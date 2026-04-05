import asyncio
import json as json_module
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from glass.audit import AuditTrail, AuditedTimer, build_proof_bundle, content_hash, verify_seal
from glass.auth import BearerAuthMiddleware
from glass.calibration import (
    CalibrationReport,
    GroundTruthJudgment,
    compute_calibration,
    list_judgments,
    record_judgment,
)
from glass.config import Settings
from glass.db import (
    delete_memory,
    get_audit_trail,
    get_response,
    init_db,
    list_memory,
    list_responses,
    population_report,
    save_response,
    update_compliance,
)
from glass.decomposer import check_premises, decompose_claims
from glass.generator import detect_backend, generate
from glass.logging_config import RequestLoggingMiddleware, configure_logging
from glass.models import AuditEvent, ComplianceMetadata, GlassResponse, QueryRequest, StatusResponse
from glass.pdf_export import generate_proof_pdf
from glass.verifier import verify_claims

# Configure structured JSON logging before anything else
configure_logging()

logger = logging.getLogger("glass")

settings = Settings.from_env()

# Cached backend — detected once at startup, refreshed via /api/status if needed
_cached_backend: str | None = None
_backend_detected: bool = False


async def _get_backend() -> str | None:
    """Return cached backend, detecting on first call."""
    global _cached_backend, _backend_detected
    if not _backend_detected:
        http_client = getattr(app.state, "http_client", None)
        _cached_backend = await detect_backend(settings, http_client=http_client)
        _backend_detected = True
    return _cached_backend


async def _refresh_backend() -> str | None:
    """Force re-detection of backend (e.g., if Ollama was started after Glass)."""
    global _cached_backend, _backend_detected
    http_client = getattr(app.state, "http_client", None)
    _cached_backend = await detect_backend(settings, http_client=http_client)
    _backend_detected = True
    return _cached_backend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    init_db(settings.db_path)

    # Create lifespan-scoped httpx client for connection pooling.
    # Eliminates per-call TCP+TLS handshakes — 4 LLM calls per query benefit significantly.
    app.state.http_client = httpx.AsyncClient(timeout=120.0)

    # Create singleton Anthropic client if API key is configured
    app.state.anthropic_client = None
    if settings.anthropic_api_key:
        try:
            import anthropic
            app.state.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        except ImportError:
            logger.warning("anthropic package not installed; Claude backend unavailable")

    # Detect backend once at startup instead of probing on every request
    await _get_backend()
    logger.info("Glass started — backend: %s", _cached_backend or "none")
    yield
    # Clean up pooled clients
    await app.state.http_client.aclose()
    if app.state.anthropic_client is not None:
        await app.state.anthropic_client.close()


app = FastAPI(title="Glass", description="AI that shows its work — all of it", lifespan=lifespan)

# Add structured logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add bearer token auth — only active when GLASS_API_TOKEN is set.
# Health probes and static assets are always public.
app.add_middleware(BearerAuthMiddleware)


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

    # Retrieve pooled clients from app.state for connection reuse
    http_client = getattr(app.state, "http_client", None)
    anthropic_client = getattr(app.state, "anthropic_client", None)

    trail = AuditTrail()

    # Generate response with reasoning trace — record failure if it happens
    try:
        raw_response, reasoning_trace = await generate(req.query, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client)
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
    premise_flags = await check_premises(req.query, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client)

    # Decompose into claims
    claims = await decompose_claims(raw_response, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client)

    # Check each claim for consistency
    claims = await verify_claims(claims, reasoning_trace, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client)

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


@app.get("/api/response/{response_id}/bundle.pdf")
async def export_proof_bundle_pdf(response_id: str):
    """Export a proof bundle as a formatted PDF document.

    Generates a professional PDF with header, self-attestation disclosure,
    claims table, audit trail, provenance seal, verification instructions,
    reviewer signature block, and EU AI Act Article 12 reference.

    "My legal counsel doesn't accept JSON files. She needs a document with
    a header, a date, and something that looks like a signature block."
    — product_manager_dan, feedback round 4
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
            message = "Stored seal does not match recomputed chain"

    bundle["seal_status"] = {
        "chain_intact": is_valid,
        "message": message,
        "events_checked": len(resp.audit_trail),
    }

    pdf_bytes = generate_proof_pdf(bundle)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="glass-proof-{response_id[:8]}.pdf"',
        },
    )


@app.get("/api/population")
async def get_population_report(
    start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    end: str | None = Query(None, description="End date YYYY-MM-DD"),
):
    """Population report for auditor period sampling.

    Returns a summary of all responses in the date range including query hash
    (SHA-256 of query text for privacy), seal verification status, backend used,
    and claim status counts.
    """
    return population_report(settings.db_path, start=start, end=end)


@app.patch("/api/response/{response_id}/compliance")
async def patch_compliance(response_id: str, body: ComplianceMetadata):
    """Update compliance metadata on a stored response.

    Fields: control_refs, retention_class, retention_period_years,
    legal_hold, reviewed_by, reviewed_at.
    """
    resp = get_response(settings.db_path, response_id)
    if resp is None:
        raise HTTPException(status_code=404, detail="Response not found")

    if not update_compliance(settings.db_path, response_id, body):
        raise HTTPException(status_code=500, detail="Failed to update compliance metadata")

    return {"status": "updated", "response_id": response_id, "compliance": body.model_dump()}


# --- Health probes (liveness + readiness split for k8s) ---
# SRE feedback: "Health endpoint conflates liveness and readiness"
# — sre_on_call, feedback round 3

@app.get("/healthz")
async def healthz():
    """Liveness probe — returns 200 if the process is running.

    This endpoint should ALWAYS return 200 as long as the Python process
    is alive and the HTTP server is accepting connections. It does NOT
    check backend availability or database state.
    """
    return {"status": "alive"}


@app.get("/readyz")
async def readyz():
    """Readiness probe — returns 200 only if Glass can serve queries.

    Checks:
    1. LLM backend is available (cached detection)
    2. Database is accessible (can connect and query)

    Returns 503 if not ready, with details about what's missing.
    """
    checks = {}
    ready = True

    # Check LLM backend
    backend = await _get_backend()
    if backend:
        checks["llm_backend"] = {"status": "ok", "backend": backend}
    else:
        checks["llm_backend"] = {"status": "unavailable", "backend": None}
        ready = False

    # Check database
    try:
        import sqlite3
        conn = sqlite3.connect(settings.db_path, timeout=2)
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = {"status": "ok", "path": settings.db_path}
    except Exception as exc:
        checks["database"] = {"status": "error", "detail": str(exc)}
        ready = False

    if not ready:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks},
        )

    return {"status": "ready", "checks": checks}


@app.get("/api/memory")
async def memory_list():
    return list_memory(settings.db_path)


@app.delete("/api/memory/{memory_id}")
async def memory_delete(memory_id: str):
    if not delete_memory(settings.db_path, memory_id):
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"status": "deleted"}


# --- SSE Streaming Query Endpoint ---
# "Glass should never fake its own process." The previous UI used setTimeout
# timers to simulate pipeline stages. This endpoint streams real events as
# each stage completes, replacing animation with ground truth.

@app.post("/api/query/stream")
async def query_stream(req: QueryRequest):
    """Submit a query and receive Server-Sent Events as each pipeline stage completes.

    Events:
      - stage: {name, status} — pipeline stage started/completed
      - result: full GlassResponse JSON — final result
      - error: {detail} — if something goes wrong

    This replaces fake setTimeout animation with real pipeline progress.
    A transparency tool must not simulate its own process.
    """
    backend = await _get_backend()
    if backend is None:
        async def error_stream():
            yield f"event: error\ndata: {json_module.dumps({'detail': 'No model backend is available.'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_stream():
        http_client = getattr(app.state, "http_client", None)
        anthropic_client = getattr(app.state, "anthropic_client", None)

        trail = AuditTrail()

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json_module.dumps(data)}\n\n"

        # Stage 1: Generate
        yield sse("stage", {"name": "generate", "status": "started"})
        try:
            raw_response, reasoning_trace = await generate(req.query, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client)
        except Exception as exc:
            logger.error("Generation failed: %s", exc)
            trail.record(
                operation="llm_call",
                description=f"Generate response — FAILED: {type(exc).__name__}: {exc}",
                backend=backend, latency_ms=0, bytes_sent=len(req.query.encode()),
                bytes_received=0, destination="error",
            )
            yield sse("error", {"detail": f"LLM generation failed: {exc}"})
            return
        yield sse("stage", {"name": "generate", "status": "done"})

        # Stage 2: Premise check + Decompose (in parallel)
        yield sse("stage", {"name": "decompose", "status": "started"})
        premise_flags, claims = await asyncio.gather(
            check_premises(req.query, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client),
            decompose_claims(raw_response, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client),
        )
        yield sse("stage", {"name": "decompose", "status": "done"})

        # Stage 3: Verify claims
        yield sse("stage", {"name": "verify", "status": "started"})
        claims = await verify_claims(claims, reasoning_trace, backend, settings, trail, http_client=http_client, anthropic_client=anthropic_client)
        yield sse("stage", {"name": "verify", "status": "done"})

        # Stage 4: Audit + Seal
        yield sse("stage", {"name": "seal", "status": "started"})
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

        with AuditedTimer() as timer:
            save_response(settings.db_path, response)
        trail.record(
            operation="db_write",
            description="Save response to local SQLite database",
            backend=None, latency_ms=timer.elapsed_ms,
            bytes_sent=0, bytes_received=0,
            destination="local/sqlite",
            content_hash=content_hash(response.id),
        )

        response.audit_trail = trail.to_list()
        response.provenance_seal = trail.seal()
        save_response(settings.db_path, response, upsert=True)
        yield sse("stage", {"name": "seal", "status": "done"})

        # Final result
        yield sse("result", response.model_dump())

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --- Calibration Endpoints ---
# The contrarian's challenge: "Glass is building receipts without guarantees."
# Calibration answers: what fraction of 'Consistent' claims are actually true?

@app.post("/api/calibrate")
async def submit_judgment(judgment: GroundTruthJudgment):
    """Submit a ground-truth judgment for a specific claim.

    This records whether a claim Glass labeled 'consistent', 'uncertain',
    or 'unverifiable' was actually correct, incorrect, or ambiguous in
    the real world. Over time, these judgments build a calibration profile.
    """
    try:
        result = record_judgment(settings.db_path, judgment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@app.get("/api/calibration")
async def get_calibration(backend: str | None = Query(None, description="Filter by backend")):
    """Get calibration metrics computed from all ground-truth judgments.

    Returns per-status accuracy, overall accuracy, and calibration gap.
    The calibration gap measures the difference between the implied accuracy
    of a 'consistent' label (100%) and the observed accuracy. A gap of 0
    means perfect calibration; a gap of 0.3 means 30% of 'consistent'
    claims were actually incorrect.
    """
    return compute_calibration(settings.db_path, backend=backend)


@app.get("/api/calibration/judgments")
async def get_judgments(response_id: str | None = Query(None, description="Filter by response ID")):
    """List recorded ground-truth judgments."""
    return list_judgments(settings.db_path, response_id=response_id)


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
