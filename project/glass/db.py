import json
import sqlite3
from contextlib import contextmanager

from glass.models import AuditEvent, Claim, GlassResponse, MemoryEntry


@contextmanager
def get_conn(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                raw_response TEXT NOT NULL,
                reasoning_trace TEXT NOT NULL,
                claims TEXT NOT NULL,
                premise_flags TEXT NOT NULL,
                audit_trail TEXT NOT NULL DEFAULT '[]',
                provenance_seal TEXT NOT NULL DEFAULT '',
                backend TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source_response_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Migrate: add audit_trail column if missing (upgrades from pre-audit schema)
        try:
            conn.execute("SELECT audit_trail FROM responses LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE responses ADD COLUMN audit_trail TEXT NOT NULL DEFAULT '[]'")
        # Migrate: add provenance_seal column if missing (upgrades from pre-seal schema)
        try:
            conn.execute("SELECT provenance_seal FROM responses LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE responses ADD COLUMN provenance_seal TEXT NOT NULL DEFAULT ''")


def save_response(db_path: str, resp: GlassResponse, upsert: bool = False) -> None:
    with get_conn(db_path) as conn:
        if upsert:
            conn.execute(
                "INSERT OR REPLACE INTO responses (id, query, raw_response, reasoning_trace, claims, premise_flags, audit_trail, provenance_seal, backend, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    resp.id,
                    resp.query,
                    resp.raw_response,
                    resp.reasoning_trace,
                    json.dumps([c.model_dump() for c in resp.claims]),
                    json.dumps(resp.premise_flags),
                    json.dumps([e.model_dump() for e in resp.audit_trail]),
                    resp.provenance_seal,
                    resp.backend,
                    resp.timestamp,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO responses (id, query, raw_response, reasoning_trace, claims, premise_flags, audit_trail, provenance_seal, backend, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    resp.id,
                    resp.query,
                    resp.raw_response,
                    resp.reasoning_trace,
                    json.dumps([c.model_dump() for c in resp.claims]),
                    json.dumps(resp.premise_flags),
                    json.dumps([e.model_dump() for e in resp.audit_trail]),
                    resp.provenance_seal,
                    resp.backend,
                    resp.timestamp,
                ),
            )


def _row_to_response(row: sqlite3.Row) -> GlassResponse:
    audit_raw = row["audit_trail"] if "audit_trail" in row.keys() else "[]"
    seal = row["provenance_seal"] if "provenance_seal" in row.keys() else ""
    return GlassResponse(
        id=row["id"],
        query=row["query"],
        raw_response=row["raw_response"],
        reasoning_trace=row["reasoning_trace"],
        claims=[Claim(**c) for c in json.loads(row["claims"])],
        premise_flags=json.loads(row["premise_flags"]),
        audit_trail=[AuditEvent(**e) for e in json.loads(audit_raw)],
        provenance_seal=seal,
        backend=row["backend"],
        timestamp=row["timestamp"],
    )


def get_response(db_path: str, response_id: str) -> GlassResponse | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM responses WHERE id = ?", (response_id,)).fetchone()
        if row is None:
            return None
        return _row_to_response(row)


def list_responses(db_path: str, limit: int = 50, offset: int = 0) -> list[GlassResponse]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM responses ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [_row_to_response(r) for r in rows]


def get_audit_trail(db_path: str, response_id: str) -> list[AuditEvent] | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT audit_trail FROM responses WHERE id = ?", (response_id,)).fetchone()
        if row is None:
            return None
        return [AuditEvent(**e) for e in json.loads(row["audit_trail"])]


def list_memory(db_path: str) -> list[MemoryEntry]:
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT * FROM memory ORDER BY last_accessed DESC").fetchall()
        return [MemoryEntry(**dict(r)) for r in rows]


def delete_memory(db_path: str, memory_id: str) -> bool:
    with get_conn(db_path) as conn:
        cursor = conn.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0
