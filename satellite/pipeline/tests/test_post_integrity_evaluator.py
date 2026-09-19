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



def test_ledger_flags_change_stress_when_n_clear_ge_2():
    """Approve-with-fixes A: empty [] vs ledger flags must diverge when n_clear≥2."""
    from engines.stress import water_stress_score, vigor_stress_score

    common = dict(ndmi=-0.02, ndmi_p25_veg=-0.05, month=9, ndvi=0.35, n_clear_dates=2)
    empty = water_stress_score(stress_flags_recent=[], **common)
    flagged = water_stress_score(stress_flags_recent=[True, True], **common)
    assert empty["components"]["persistence"] is None
    assert flagged["components"]["persistence"] is not None
    assert flagged["water_stress_score"] != empty["water_stress_score"]

    v_empty = vigor_stress_score(
        ndvi=0.22, ndvi_p25_veg=0.25, stress_flags_recent=[], month=9, n_clear_dates=2
    )
    v_flagged = vigor_stress_score(
        ndvi=0.22, ndvi_p25_veg=0.25, stress_flags_recent=[True, False], month=9, n_clear_dates=2
    )
    assert v_empty["components"]["persistence"] is None
    assert v_flagged["components"]["persistence"] is not None


def test_rescore_helper_wires_flags():
    from run_ag_probability import _rescore_stress_with_ledger_flags

    props = {
        "ndvi": 0.30,
        "ndmi": -0.02,
        "ndvi_p25_veg": 0.25,
        "ndmi_p25_veg": -0.05,
        "data_quality_confidence": 80.0,
        "water_stress_score": 10.0,
        "vigor_stress_score": 10.0,
        "n_clear_dates": 1,
    }
    # n_clear=1 → keep empty-flag renorm path
    _rescore_stress_with_ledger_flags(
        props,
        water_flags=[True, True],
        vigor_flags=[True, True],
        month=9,
        n_clear_dates=1,
    )
    assert props["stress_flags_recent_water"] == []
    assert props["stress_components_water"]["persistence"] is None

    # n_clear≥2 → ledger flags feed persistence
    _rescore_stress_with_ledger_flags(
        props,
        water_flags=[True, True],
        vigor_flags=[False, True],
        month=9,
        n_clear_dates=3,
    )
    assert props["stress_flags_recent_water"] == [True, True]
    assert props["stress_flags_recent_vigor"] == [False, True]
    assert props["stress_components_water"]["persistence"] is not None
    assert props["n_clear_dates"] == 3


if __name__ == "__main__":
    test_nov1_never_late_khareef()
    test_cell_coverage_unassessable()
    test_aou_coverage_gate()
    test_persistence_not_half_from_n_clear_alone()
    test_empty_stress_flags_not_healthy()
    test_ledger_sequence_excludes_window()
    test_ledger_flags_change_stress_when_n_clear_ge_2()
    test_rescore_helper_wires_flags()
    print("OK post-integrity evaluator tests")
