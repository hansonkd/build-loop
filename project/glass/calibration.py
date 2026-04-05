"""Calibration system — empirical measurement of claim accuracy.

The contrarian's challenge: "Glass is building receipts without guarantees.
Build a calibration measurement system — what fraction of Consistent claims
are actually true?"

This module accepts ground-truth judgments for past claims and computes
calibration metrics. Over time, it answers: when Glass labels a claim
'consistent', how often is that claim actually correct?

This is tedious empirical work. Not sexy. Actually useful.
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from glass.db import get_conn, get_response


class GroundTruthJudgment(BaseModel):
    """A human reviewer's ground-truth judgment on a specific claim."""
    response_id: str
    claim_index: int
    ground_truth: Literal["correct", "incorrect", "ambiguous"]
    reviewer: str = ""
    notes: str = ""


class CalibrationScore(BaseModel):
    """Calibration metrics for a given status label."""
    status: str
    total_judged: int
    correct: int
    incorrect: int
    ambiguous: int
    accuracy: float  # correct / (correct + incorrect), excluding ambiguous
    sample_size_sufficient: bool  # >= 30 judgments for statistical significance


class CalibrationReport(BaseModel):
    """Full calibration report across all status labels."""
    total_judgments: int
    by_status: list[CalibrationScore]
    overall_accuracy: float  # across all non-ambiguous judgments
    calibration_gap: float  # difference between expected (100% for consistent) and actual
    methodology: str


def init_calibration_db(db_path: str) -> None:
    """Create the calibration judgments table if it doesn't exist."""
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calibration_judgments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id TEXT NOT NULL,
                claim_index INTEGER NOT NULL,
                claim_text TEXT NOT NULL,
                glass_status TEXT NOT NULL,
                ground_truth TEXT NOT NULL CHECK(ground_truth IN ('correct', 'incorrect', 'ambiguous')),
                reviewer TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                judged_at TEXT NOT NULL,
                UNIQUE(response_id, claim_index)
            )
        """)


def record_judgment(db_path: str, judgment: GroundTruthJudgment) -> dict:
    """Record a ground-truth judgment for a specific claim.

    Returns the stored judgment with the claim text and Glass's original status.
    Raises ValueError if the response or claim index doesn't exist.
    """
    from datetime import datetime, timezone

    resp = get_response(db_path, judgment.response_id)
    if resp is None:
        raise ValueError(f"Response {judgment.response_id} not found")

    if judgment.claim_index < 0 or judgment.claim_index >= len(resp.claims):
        raise ValueError(
            f"Claim index {judgment.claim_index} out of range "
            f"(response has {len(resp.claims)} claims)"
        )

    claim = resp.claims[judgment.claim_index]

    init_calibration_db(db_path)

    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO calibration_judgments
            (response_id, claim_index, claim_text, glass_status, ground_truth,
             reviewer, notes, judged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                judgment.response_id,
                judgment.claim_index,
                claim.text,
                claim.status,
                judgment.ground_truth,
                judgment.reviewer,
                judgment.notes,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    return {
        "response_id": judgment.response_id,
        "claim_index": judgment.claim_index,
        "claim_text": claim.text,
        "glass_status": claim.status,
        "ground_truth": judgment.ground_truth,
        "reviewer": judgment.reviewer,
    }


def compute_calibration(db_path: str, backend: str | None = None) -> CalibrationReport:
    """Compute calibration metrics from all recorded ground-truth judgments.

    Optionally filter by backend to see calibration per model.
    Returns a CalibrationReport with per-status breakdowns and overall accuracy.
    """
    init_calibration_db(db_path)

    with get_conn(db_path) as conn:
        if backend:
            rows = conn.execute(
                """SELECT cj.glass_status, cj.ground_truth, cj.claim_text
                FROM calibration_judgments cj
                JOIN responses r ON cj.response_id = r.id
                WHERE r.backend = ?""",
                (backend,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT glass_status, ground_truth, claim_text FROM calibration_judgments"
            ).fetchall()

    if not rows:
        return CalibrationReport(
            total_judgments=0,
            by_status=[],
            overall_accuracy=0.0,
            calibration_gap=0.0,
            methodology=_methodology_text(),
        )

    # Aggregate by glass_status
    status_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        status = row["glass_status"]
        gt = row["ground_truth"]
        if status not in status_counts:
            status_counts[status] = {"correct": 0, "incorrect": 0, "ambiguous": 0}
        status_counts[status][gt] += 1

    by_status = []
    total_correct = 0
    total_incorrect = 0
    total_ambiguous = 0

    for status, counts in sorted(status_counts.items()):
        correct = counts["correct"]
        incorrect = counts["incorrect"]
        ambiguous = counts["ambiguous"]
        total = correct + incorrect + ambiguous
        non_ambiguous = correct + incorrect

        total_correct += correct
        total_incorrect += incorrect
        total_ambiguous += ambiguous

        accuracy = correct / non_ambiguous if non_ambiguous > 0 else 0.0

        by_status.append(CalibrationScore(
            status=status,
            total_judged=total,
            correct=correct,
            incorrect=incorrect,
            ambiguous=ambiguous,
            accuracy=round(accuracy, 4),
            sample_size_sufficient=total >= 30,
        ))

    overall_non_ambiguous = total_correct + total_incorrect
    overall_accuracy = total_correct / overall_non_ambiguous if overall_non_ambiguous > 0 else 0.0

    # Calibration gap: for "consistent" claims, the implied accuracy is 100%.
    # The gap is the difference between that expectation and reality.
    consistent_score = next((s for s in by_status if s.status == "consistent"), None)
    calibration_gap = 0.0
    if consistent_score and consistent_score.accuracy > 0:
        calibration_gap = round(1.0 - consistent_score.accuracy, 4)

    return CalibrationReport(
        total_judgments=len(rows),
        by_status=by_status,
        overall_accuracy=round(overall_accuracy, 4),
        calibration_gap=calibration_gap,
        methodology=_methodology_text(),
    )


def list_judgments(db_path: str, response_id: str | None = None) -> list[dict]:
    """List recorded ground-truth judgments, optionally filtered by response_id."""
    init_calibration_db(db_path)

    with get_conn(db_path) as conn:
        if response_id:
            rows = conn.execute(
                "SELECT * FROM calibration_judgments WHERE response_id = ? ORDER BY claim_index",
                (response_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calibration_judgments ORDER BY judged_at DESC LIMIT 200"
            ).fetchall()

    return [dict(r) for r in rows]


def _methodology_text() -> str:
    return (
        "Calibration is computed from human ground-truth judgments submitted via "
        "/api/calibrate. Each judgment records whether a claim Glass labeled "
        "'consistent', 'uncertain', or 'unverifiable' was actually correct, "
        "incorrect, or ambiguous in the real world. Accuracy = correct / "
        "(correct + incorrect), excluding ambiguous judgments. A sample size "
        "of >= 30 judgments per status label is required for statistical "
        "significance. The calibration gap measures the difference between "
        "the implied accuracy of a 'consistent' label (100%) and the observed "
        "accuracy. A gap of 0 means perfect calibration; a gap of 0.3 means "
        "30% of 'consistent' claims were actually incorrect."
    )
