# Glass

AI that shows its work -- honest by architecture, not by instruction.

Every query produces an auditable proof chain: raw LLM output, decomposed claims, consistency checks, and a tamper-evident SHA-256 provenance seal. Anyone can independently verify the chain without trusting Glass.

## Quick Start

```bash
cd project
pip install -e .
glass
```

Open http://localhost:7777

## Dev Setup

```bash
# Install with dev dependencies (pytest, pytest-asyncio)
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_audit.py -v

# Run a single test by name
pytest -k test_verify_seal
```

## Backends

Glass auto-detects available backends in priority order:

1. **Ollama (local, default):** Install [Ollama](https://ollama.com), pull a model (`ollama pull llama3.2`), and run `ollama serve`. No data leaves your machine.
2. **OpenRouter (cloud):** Set `OPENROUTER_API_KEY`. Routes through openrouter.ai.
3. **Claude (cloud):** Set `ANTHROPIC_API_KEY`. Requires `pip install -e ".[claude]"`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OPENROUTER_API_KEY` | (none) | Enables OpenRouter backend |
| `OPENROUTER_MODEL` | `anthropic/claude-sonnet-4` | OpenRouter model to use |
| `ANTHROPIC_API_KEY` | (none) | Enables Claude backend |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `GLASS_API_TOKEN` | (none) | Bearer token for API auth; unset = open access |
| `GLASS_DB_PATH` | `glass.db` | SQLite database path |
| `GLASS_HOST` | `0.0.0.0` | Server bind address |
| `GLASS_PORT` | `7777` | Server port |

## API Endpoints

### Core

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Landing page (static HTML) |
| `POST` | `/api/query` | Submit a query. Returns `GlassResponse` with claims, audit trail, and provenance seal |
| `GET` | `/api/status` | Backend status and model info (refreshes backend detection) |
| `GET` | `/api/history?limit=50&offset=0` | List past responses (paginated) |
| `GET` | `/api/response/{id}` | Get a single response by ID |
| `GET` | `/api/response/{id}/audit` | Get just the audit trail for a response |

### Verification and Proof

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/response/{id}/verify` | Recompute provenance chain and verify the seal is intact |
| `GET` | `/api/response/{id}/bundle` | Export self-contained JSON proof bundle for independent verification |
| `GET` | `/api/response/{id}/bundle.pdf` | Export proof bundle as formatted PDF with signature block |

### Streaming

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/query/stream` | Submit a query and receive Server-Sent Events as each pipeline stage completes. Events: `stage`, `result`, `error` |

### Calibration

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/calibrate` | Submit a ground-truth judgment for a specific claim (correct/incorrect/ambiguous) |
| `GET` | `/api/calibration?backend=ollama` | Get calibration metrics: per-status accuracy, overall accuracy, calibration gap |
| `GET` | `/api/calibration/judgments?response_id=...` | List recorded ground-truth judgments |

### Compliance

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/population?start=YYYY-MM-DD&end=YYYY-MM-DD` | Population report for auditor period sampling. Returns query hashes, seal status, claim counts |
| `PATCH` | `/api/response/{id}/compliance` | Update compliance metadata (control_refs, retention_class, retention_period_years, legal_hold, reviewed_by, reviewed_at) |

### Memory

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/memory` | List memory entries |
| `DELETE` | `/api/memory/{id}` | Delete a memory entry |

### Health (Kubernetes-ready)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/healthz` | Liveness probe -- always 200 if process is alive |
| `GET` | `/readyz` | Readiness probe -- 200 only if LLM backend and DB are available |

## Architecture

```
query -> generator.py (LLM call)
      -> decomposer.py (extract claims)
      -> verifier.py (consistency check)
      -> audit.py (SHA-256 hash chain + seal)
      -> db.py (SQLite with WAL mode)
      -> proof bundle (JSON or PDF export)
```

All LLM calls use connection-pooled httpx clients (created once at startup, reused for the app lifetime) to avoid per-call TCP+TLS handshake overhead. The Anthropic SDK client is also a singleton.

## Authentication

Set `GLASS_API_TOKEN` to enable Bearer token auth on all `/api/*` endpoints. Health probes (`/healthz`, `/readyz`) and static assets are always public. When unset, Glass runs in open-access mode (suitable for local development).

```bash
export GLASS_API_TOKEN="your-secret-token"
curl -H "Authorization: Bearer your-secret-token" http://localhost:7777/api/status
```

## Calibration

Glass now supports empirical calibration measurement. Submit ground-truth judgments for past claims via `POST /api/calibrate`, then query `GET /api/calibration` to see what fraction of "consistent" claims were actually correct. This answers the hard question: when Glass says "consistent", how often is that actually true?

```bash
# Submit a judgment
curl -X POST http://localhost:7777/api/calibrate \
  -H "Content-Type: application/json" \
  -d '{"response_id": "...", "claim_index": 0, "ground_truth": "correct", "reviewer": "alice"}'

# View calibration metrics
curl http://localhost:7777/api/calibration
```
