# Glass — Architecture

## Overview

Glass is a web application with a Python backend and a lightweight browser frontend. The core pipeline is:

```
User Query → Generator → Decomposer → Verifier → Seal → Renderer
                ↕              ↕            ↕        ↕
              Audit Trail (logs every LLM call, latency, data flow)
                                                     ↓
                                              Provenance Seal (hash chain)
```

Each stage is a distinct module. The generator produces a response, the decomposer breaks it into claims, the verifier assesses each claim, the sealer computes a cryptographic hash chain over the audit trail, and the renderer presents everything with full transparency. The audit trail captures every operation across all stages. The provenance seal proves the trail has not been tampered with.

## Pipeline Stages

### 1. Generator (`glass/generator.py`)

Takes a user query and produces a raw response with chain-of-thought reasoning.

- Connects to Ollama (default) or Claude API (opt-in) for inference
- System prompt instructs the model to think step-by-step and be explicit about uncertainty
- Returns both the final answer and the full reasoning trace
- If no model backend is available, returns a clear error — never a fabricated response
- Every LLM call is recorded in the audit trail with timing and token metadata

### 2. Decomposer (`glass/decomposer.py`)

Takes the generator's response and extracts individual claims.

- Each claim is a single, atomic assertion that can be independently evaluated
- Claims are extracted via a second LLM call with a structured output format
- Output: a list of `Claim` objects, each with the claim text and its source location in the original response
- The decomposition LLM call is recorded in the audit trail

### 3. Verifier (`glass/verifier.py`)

Takes the list of claims and assesses each one independently.

- For each claim, the verifier attempts to determine if it's supported, uncertain, or unverifiable
- Verification strategies (applied in order):
  1. **Self-consistency**: Does the claim contradict other claims in the same response?
  2. **Source check**: Can the claim be traced to the model's reasoning chain?
  3. **Confidence assessment**: How hedged or definitive was the original statement?
- Each claim gets a tag: `verified`, `uncertain`, or `unverifiable`
- Each claim gets a short evidence string explaining the tag
- The verifier also checks the user's original query for false premises and flags them
- The verification LLM call is recorded in the audit trail

### 4. Audit Trail (`glass/audit.py`)

Captures every operation the system performs during a query lifecycle.

- Each audit event includes: timestamp, operation type, backend used, latency in milliseconds, payload sizes (bytes sent/received), and a truncated hash of request/response content
- Each event also carries a `chain_hash`: a SHA-256 hash of the event's content combined with the previous event's chain_hash, forming a linked chain
- Operation types: `llm_call` (any LLM invocation), `network_request` (any external HTTP call), `db_write` (any storage operation)
- Events are collected in-memory during request processing and persisted atomically with the response
- The audit trail is exposed via the API and rendered in the frontend as an expandable timeline
- No audit data is ever sent to external services

### 4a. Provenance Seal (`glass/audit.py`)

After all pipeline stages complete, the audit trail is sealed with a provenance hash.

- The seal is the `chain_hash` of the final event in the audit trail
- Anyone can verify the seal by iterating through the events and recomputing each chain_hash from the event content + previous hash
- If any event is modified, the seal will not match the recomputed chain
- The seal is stored as a top-level field in the Response object and displayed prominently in the UI
- Verification is a pure local computation -- no external service, no secret key, no trust required
- The `/api/response/{id}/verify` endpoint recomputes the chain and reports whether the seal is intact

### 5. Proof Bundle Export (`glass/audit.py`)

After a response is complete and sealed, it can be exported as a self-contained proof bundle.

- The bundle is a JSON document containing: query, response, claims, audit trail, provenance seal, backend, timestamp, and verification instructions
- The `verification_instructions` field contains a plain-language description of the SHA-256 chain algorithm, enabling any third party to write their own verifier
- The bundle includes a `bundle_generated_at` timestamp and a `glass_version` field for provenance
- Export is available via `GET /api/response/{id}/bundle` and via a download button in the UI
- The bundle is designed for portability: email it, archive it, attach it to a compliance report, or verify it on an air-gapped machine
- No secrets, API keys, or user-identifying information are included in the bundle

### 6. Renderer (Frontend)

Takes the verified response and presents it in the browser with a **process-first layout**.

- The UI is divided into two columns on desktop: left column shows the process (audit timeline + reasoning trace), right column shows the result (answer + claims). On mobile, process stacks above result.
- The audit timeline is always visible and expanded by default — it is the primary evidence of what Glass did. Each operation appears as a card with timing, data flow direction, destination, and a local/external indicator.
- The reasoning trace is displayed in a dedicated panel, not hidden behind a toggle.
- The answer section displays the response with inline claim annotations (color-coded by verification status).
- Each claim is clickable — expanding it shows the evidence and verification reasoning.
- A header bar shows the overall verification summary (e.g., "5 verified, 2 uncertain, 1 unverifiable") plus total pipeline time and data flow totals.
- If a cloud backend is active, a persistent banner indicates "Cloud mode — data leaves your machine" with the exact destination shown.
- The audit trail visually distinguishes local operations (green) from external operations (amber).
- A pipeline stage indicator shows which stages have completed and their individual timings.

## Data Model

### Claim
```
{
  "text": string,           // The claim itself
  "status": "verified" | "uncertain" | "unverifiable",
  "evidence": string,       // Why this status was assigned
  "source_span": [int, int] // Character offsets in the original response
}
```

### AuditEvent
```
{
  "timestamp": string,        // ISO 8601
  "operation": string,        // "llm_call" | "network_request" | "db_write"
  "description": string,      // Human-readable description (e.g., "Generate response via openrouter")
  "backend": string | null,   // Which backend was used
  "latency_ms": int,          // How long the operation took
  "bytes_sent": int,          // Payload size sent
  "bytes_received": int,      // Payload size received
  "destination": string,      // Where data went (e.g., "openrouter.ai", "local/ollama", "local/sqlite")
  "content_hash": string,     // Truncated SHA-256 of the response content
  "chain_hash": string        // SHA-256 hash linking this event to the previous (provenance chain)
}
```

### Response
```
{
  "id": string,
  "query": string,
  "raw_response": string,
  "reasoning_trace": string,
  "claims": [Claim],
  "premise_flags": [string],  // Issues found in the user's query
  "audit_trail": [AuditEvent], // Full operation log for this response
  "provenance_seal": string,  // Hash chain head -- proves the audit trail is unaltered
  "backend": string,          // "ollama" | "openrouter" | "claude"
  "timestamp": string
}
```

### Memory Entry
```
{
  "id": string,
  "key": string,            // What this memory is about
  "value": string,          // The remembered information
  "source_response_id": string,
  "created_at": string,
  "last_accessed": string,
  "access_count": int
}
```

## API Endpoints

All endpoints are served by FastAPI.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves the frontend HTML |
| POST | `/api/query` | Submit a query, returns a full Response object with audit trail |
| GET | `/api/history` | List past responses (paginated) |
| GET | `/api/response/{id}` | Get a specific response with all claims and audit trail |
| GET | `/api/response/{id}/audit` | Get just the audit trail for a specific response |
| GET | `/api/response/{id}/verify` | Recompute provenance chain and verify the seal is intact |
| GET | `/api/response/{id}/bundle` | Export a self-contained proof bundle (JSON) for independent verification |
| GET | `/api/memory` | List all memory entries |
| DELETE | `/api/memory/{id}` | Delete a specific memory entry |
| GET | `/api/status` | Backend health check (is Ollama running? which model?) |

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: Vanilla HTML/CSS/JS — no build step, no framework, served as static files by FastAPI
- **LLM Backend**: Ollama (default, local), OpenRouter (opt-in via `OPENROUTER_API_KEY`), Claude API (opt-in via `ANTHROPIC_API_KEY`)
- **Storage**: SQLite via Python's built-in `sqlite3` — one file, `glass.db`, in the project root
- **Dependencies**: `fastapi`, `uvicorn`, `httpx` (for Ollama/OpenRouter/Claude API calls), `anthropic` (optional, for Claude)

## File Structure

```
project/
├── glass/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, routes, startup
│   ├── generator.py     # LLM interaction (Ollama + Claude)
│   ├── decomposer.py    # Claim extraction
│   ├── verifier.py      # Claim verification
│   ├── audit.py         # Audit trail collection and persistence
│   ├── models.py        # Pydantic models (Claim, AuditEvent, Response, Memory)
│   ├── db.py            # SQLite operations
│   └── config.py        # Settings, backend selection
├── static/
│   ├── index.html        # Single-page app
│   ├── style.css         # Dark theme, claim annotations, audit trail
│   └── app.js            # Frontend logic, rendering, audit timeline
├── pyproject.toml         # Project metadata + dependencies
└── README.md              # How to run
```

## Graceful Degradation

If Ollama is not running and no API keys are set:
- `/api/status` returns `{"backend": null, "message": "No LLM backend available"}`
- `/api/query` returns a clear error: "No model backend is available. Install Ollama or set OPENROUTER_API_KEY or ANTHROPIC_API_KEY."
- The frontend displays this message prominently instead of a chat interface
- The app still starts and serves the UI — it never crashes due to a missing backend

## Deployment

- **Demo (port 7777)**: The Glass app runs on port 7777 with OpenRouter as the default cloud backend
- **Landing page (port 80)**: A separate static site in `landing-page/` describes what Glass is and links to the demo
