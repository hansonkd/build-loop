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
