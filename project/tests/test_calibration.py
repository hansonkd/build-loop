"""Tests for calibration system: ground-truth judgments and calibration metrics."""

import os
import tempfile

from glass.calibration import (
    GroundTruthJudgment,
    compute_calibration,
    init_calibration_db,
    list_judgments,
    record_judgment,
)
from glass.db import init_db, save_response
from glass.models import Claim, GlassResponse


def _make_response(id: str = "cal-1", backend: str = "ollama") -> GlassResponse:
    return GlassResponse(
        id=id,
        query="What is the speed of light?",
        raw_response="The speed of light is approximately 299,792,458 meters per second.",
        reasoning_trace="Known physical constant.",
        claims=[
            Claim(text="Speed of light is 299,792,458 m/s", status="consistent", evidence="Known constant", source_span=[0, 60]),
            Claim(text="Light travels in a vacuum", status="consistent", evidence="Standard physics", source_span=[10, 40]),
            Claim(text="Einstein predicted this", status="uncertain", evidence="Historically nuanced", source_span=[20, 50]),
        ],
        premise_flags=[],
        audit_trail=[],
        provenance_seal="",
        backend=backend,
        timestamp="2026-04-04T12:00:00Z",
    )


def test_record_judgment():
    """Record a ground-truth judgment and retrieve it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response())

        result = record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1",
            claim_index=0,
            ground_truth="correct",
            reviewer="alice@example.com",
            notes="Verified against NIST reference",
        ))

        assert result["glass_status"] == "consistent"
        assert result["ground_truth"] == "correct"
        assert result["claim_text"] == "Speed of light is 299,792,458 m/s"


def test_record_judgment_invalid_response():
    """Recording a judgment for nonexistent response raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)

        try:
            record_judgment(db_path, GroundTruthJudgment(
                response_id="nonexistent",
                claim_index=0,
                ground_truth="correct",
            ))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not found" in str(e)


def test_record_judgment_invalid_claim_index():
    """Recording a judgment for out-of-range claim index raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response())

        try:
            record_judgment(db_path, GroundTruthJudgment(
                response_id="cal-1",
                claim_index=99,
                ground_truth="incorrect",
            ))
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "out of range" in str(e)


def test_compute_calibration_empty():
    """Calibration with no judgments returns zero metrics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)

        report = compute_calibration(db_path)
        assert report.total_judgments == 0
        assert report.overall_accuracy == 0.0
        assert len(report.by_status) == 0


def test_compute_calibration_with_judgments():
    """Calibration computes correct metrics from multiple judgments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response())

        # Claim 0: consistent -> correct
        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=0, ground_truth="correct",
        ))
        # Claim 1: consistent -> incorrect
        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=1, ground_truth="incorrect",
        ))
        # Claim 2: uncertain -> correct
        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=2, ground_truth="correct",
        ))

        report = compute_calibration(db_path)
        assert report.total_judgments == 3

        # Check consistent status: 1 correct, 1 incorrect = 50% accuracy
        consistent_score = next(s for s in report.by_status if s.status == "consistent")
        assert consistent_score.correct == 1
        assert consistent_score.incorrect == 1
        assert consistent_score.accuracy == 0.5

        # Calibration gap: 1.0 - 0.5 = 0.5
        assert report.calibration_gap == 0.5

        # Uncertain status: 1 correct, 0 incorrect = 100% accuracy
        uncertain_score = next(s for s in report.by_status if s.status == "uncertain")
        assert uncertain_score.correct == 1
        assert uncertain_score.accuracy == 1.0


def test_list_judgments():
    """List judgments with and without response_id filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response())

        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=0, ground_truth="correct",
        ))
        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=1, ground_truth="incorrect",
        ))

        # All judgments
        all_j = list_judgments(db_path)
        assert len(all_j) == 2

        # Filtered by response_id
        filtered = list_judgments(db_path, response_id="cal-1")
        assert len(filtered) == 2

        # Nonexistent response
        empty = list_judgments(db_path, response_id="nonexistent")
        assert len(empty) == 0


def test_judgment_upsert():
    """Recording a judgment for the same claim twice updates it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        init_db(db_path)
        save_response(db_path, _make_response())

        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=0, ground_truth="correct",
        ))
        record_judgment(db_path, GroundTruthJudgment(
            response_id="cal-1", claim_index=0, ground_truth="incorrect",
            notes="Revised after checking primary source",
        ))

        judgments = list_judgments(db_path, response_id="cal-1")
        assert len(judgments) == 1
        assert judgments[0]["ground_truth"] == "incorrect"
