"""Tests for db.py: database operations, population report, compliance update."""

import os
import tempfile

from glass.db import (
    get_response,
    init_db,
    list_responses,
    population_report,
    save_response,
    update_compliance,
)
from glass.models import Claim, ComplianceMetadata, GlassResponse


def _make_response(id: str = "test-1", query: str = "What is 2+2?", backend: str = "ollama", timestamp: str = "2026-04-04T12:00:00Z") -> GlassResponse:
    return GlassResponse(
        id=id,
        query=query,
        raw_response="The answer is 4.",
        reasoning_trace="2+2=4 by arithmetic.",
        claims=[
            Claim(text="2+2 equals 4", status="consistent", evidence="Basic arithmetic", source_span=[0, 16]),
        ],
        premise_flags=[],
        audit_trail=[],
        provenance_seal="",
        backend=backend,
        timestamp=timestamp,
    )


def test_save_and_get_response():
    """Save a response and retrieve it by ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        resp = _make_response()
        save_response(db_path, resp)
        fetched = get_response(db_path, "test-1")
        assert fetched is not None
        assert fetched.id == "test-1"
        assert fetched.query == "What is 2+2?"
        assert len(fetched.claims) == 1
        assert fetched.claims[0].status == "consistent"


def test_population_report_date_filtering():
    """Population report respects date filters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response(id="r1", timestamp="2026-04-01T10:00:00Z"))
        save_response(db_path, _make_response(id="r2", timestamp="2026-04-03T10:00:00Z"))
        save_response(db_path, _make_response(id="r3", timestamp="2026-04-05T10:00:00Z"))

        # All responses
        report = population_report(db_path)
        assert len(report) == 3

        # Date range filter
        report = population_report(db_path, start="2026-04-02", end="2026-04-04")
        assert len(report) == 1
        assert report[0]["backend"] == "ollama"
        assert report[0]["claims_count"] == 1
        assert report[0]["consistent_count"] == 1

        # Start only
        report = population_report(db_path, start="2026-04-04")
        assert len(report) == 1

        # End only
        report = population_report(db_path, end="2026-04-02")
        assert len(report) == 1


def test_compliance_update():
    """Update compliance metadata on a stored response."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response())

        meta = ComplianceMetadata(
            control_refs=["SOC2-CC7.2", "ISO27001-A.12.4.1"],
            retention_class="standard",
            retention_period_years=7,
            legal_hold=True,
            reviewed_by="alice@example.com",
            reviewed_at="2026-04-04T15:00:00Z",
        )
        assert update_compliance(db_path, "test-1", meta) is True

        fetched = get_response(db_path, "test-1")
        assert fetched is not None
        assert fetched.compliance.legal_hold is True
        assert fetched.compliance.retention_period_years == 7
        assert "SOC2-CC7.2" in fetched.compliance.control_refs
        assert fetched.compliance.reviewed_by == "alice@example.com"


def test_compliance_update_nonexistent():
    """Updating compliance on a nonexistent response returns False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        meta = ComplianceMetadata()
        assert update_compliance(db_path, "nonexistent", meta) is False
