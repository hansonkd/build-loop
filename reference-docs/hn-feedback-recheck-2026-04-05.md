# Post-Implementation Recheck — 2026-04-05

Two personas (compliance_karen, sre_on_call) re-evaluated after Tier 0-1 fixes and compliance pivot.

## Score Card

| Item | Status |
|------|--------|
| Rename Verified → Consistent | FIXED |
| PDF proof bundle export | FIXED |
| Self-attestation disclosure | FIXED |
| /healthz + /readyz split | FIXED |
| content_hash truncation | FIXED |
| Cached detect_backend() | FIXED |
| LLM failure handling in audit trail | FIXED |
| WAL mode + check_same_thread | FIXED |
| Structured JSON logging | FIXED |
| Shared llm_client.py extracted | FIXED |
| Landing page for compliance buyers | FIXED |
| Architecture doc updated | FIXED |
| Module-level httpx client (pooling) | NOT FIXED |
| Tests | NOT FIXED |
| Population report endpoint | NOT FIXED |
| Compliance metadata fields on bundle | NOT FIXED |
| Vendor security questionnaire | NOT FIXED |

## Remaining Gaps (priority order)

### SRE blockers
1. **httpx connection pooling** — every LLM call creates new TCP+TLS session. 4 calls per query × TLS handshake = compounding latency. Instantiate one client per backend at startup.
2. **Zero tests** — no pytest, no test dir, no CI. Hash chain seal is untested. Credibility blocker.
3. **Anthropic SDK re-instantiated per call** — throws away connection pool each time.

### Compliance blockers
1. **Population report endpoint** — auditors need date-filtered query listing for period sampling
2. **Compliance metadata fields** — control_refs, retention_class, legal_hold, reviewed_by on JSON bundle schema
3. **Vendor security questionnaire** — table stakes for procurement, not code
