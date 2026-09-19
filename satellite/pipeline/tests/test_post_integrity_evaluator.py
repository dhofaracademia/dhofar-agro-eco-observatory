#!/usr/bin/env python3
"""Acceptance tests — SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md P0."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

from engines.observation_integrity import (  # noqa: E402
    aou_assessability,
    cell_assessability,
    ledger_persistence_feature,
    ledger_sequence_rows,
    ledger_stress_flags,
)
from run_khareef_status import calendar_stage  # noqa: E402


def test_nov1_never_late_khareef():
    for y in (2024, 2025, 2026, 2027):
        stage, _ = calendar_stage(date(y, 11, 1))
        assert stage != "late_khareef", (y, stage)
        assert stage == "insufficient"
    # Still late inside post window
    stage, _ = calendar_stage(date(2026, 10, 15))
    assert stage == "late_khareef"


def test_cell_coverage_unassessable():
    assert cell_assessability({"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 10}) == "unassessable"
    assert cell_assessability({"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 100}) == "assessable"
    assert cell_assessability({"ndvi": None, "ndmi": 0.1, "pixel_count": 100}) == "unassessable"
    assert cell_assessability({"scl_missing": True, "ndvi": 0.4, "ndmi": 0.1, "pixel_count": 100}) == "unassessable"


def test_aou_coverage_gate():
    weak = [{"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 10} for _ in range(5)]
    status, meta = aou_assessability(weak, min_clear_fraction=0.2, min_clear_members=1)
    assert status == "unassessable"
    strong = [{"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 100} for _ in range(5)]
    status, meta = aou_assessability(strong, min_clear_fraction=0.2, min_clear_members=1)
    assert status == "assessable"
    assert meta["clear_member_count"] == 5


def test_persistence_not_half_from_n_clear_alone():
    # Single date → None (not 0.5)
    feat, n, above = ledger_persistence_feature([{"date": "2026-09-01", "ndvi": 0.4}])
    assert feat is None and n == 1
    # Two dates with real sequence → computed fraction, not hardcoded 0.5
    feat, n, above = ledger_persistence_feature(
        [
            {"date": "2026-08-01", "ndvi": 0.4},
            {"date": "2026-09-01", "ndvi": 0.5},
        ]
    )
    assert feat == 1.0 and n == 2 and above == 2
    feat2, _, above2 = ledger_persistence_feature(
        [
            {"date": "2026-08-01", "ndvi": 0.05},
            {"date": "2026-09-01", "ndvi": 0.4},
        ]
    )
    assert above2 == 1
    assert feat2 is not None and feat2 == 0.25  # (1/2)*0.5 weak


def test_empty_stress_flags_not_healthy():
    assert ledger_stress_flags([], kind="water") == []
    rows = [
        {"date": "2026-08-01", "ndvi": 0.3, "alert": "water_attention", "water_stress_score": 70},
        {"date": "2026-09-01", "ndvi": 0.3, "alert": "healthy", "water_stress_score": 20},
    ]
    flags = ledger_stress_flags(rows, kind="water")
    assert flags == [True, False]


def test_ledger_sequence_excludes_window():
    unit = {
        "observations": [
            {"date": "2026-09-01", "ndvi": 0.4, "series_scope": "aou"},
            {"date": "2026-08-01", "ndvi": 0.3, "series_scope": "window_not_aou"},
        ]
    }
    rows = ledger_sequence_rows(unit)
    assert len(rows) == 1 and rows[0]["date"] == "2026-09-01"


if __name__ == "__main__":
    test_nov1_never_late_khareef()
    test_cell_coverage_unassessable()
    test_aou_coverage_gate()
    test_persistence_not_half_from_n_clear_alone()
    test_empty_stress_flags_not_healthy()
    test_ledger_sequence_excludes_window()
    print("OK post-integrity evaluator tests")
