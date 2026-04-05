import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from glass.audit import AuditTrail, AuditedTimer, content_hash, verify_seal
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

settings = Settings.from_env()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    init_db(settings.db_path)
    yield


app = FastAPI(title="Glass", description="AI that shows its work — all of it", lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/status")
async def status() -> StatusResponse:
    backend = await detect_backend(settings)
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
    backend = await detect_backend(settings)
    if backend is None:
        raise HTTPException(
            status_code=503,
            detail="No model backend is available. Install Ollama or set ANTHROPIC_API_KEY.",
        )

    trail = AuditTrail()

    # Generate response with reasoning trace
    raw_response, reasoning_trace = await generate(req.query, backend, settings, trail)

    # Check user's premises for errors
    premise_flags = await check_premises(req.query, backend, settings, trail)

    # Decompose into claims
    claims = await decompose_claims(raw_response, backend, settings, trail)

    # Verify each claim
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
    """Recompute the provenance chain and verify the seal is intact.

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
            message = f"Stored seal does not match recomputed chain. Stored: {resp.provenance_seal[:16]}..., Computed: {recomputed[:16]}..."

    return {
        "response_id": response_id,
        "seal": resp.provenance_seal,
        "verified": is_valid,
        "message": message,
        "events_checked": len(resp.audit_trail),
    }


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
