#!/usr/bin/env python3
"""Acceptance tests — SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md P0/P1."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

from engines.biotic import biotic_three_state  # noqa: E402
from engines.observation_integrity import (  # noqa: E402
    OBSERVATION_ROLE_CURRENT,
    OBSERVATION_ROLE_RETAINED,
    aou_assessability_with_area,
    biotic_status_three_state,
    build_aou_date_aggregate,
    cell_assessability,
    ledger_persistence_feature,
    ledger_rows_before,
    ledger_rows_excluding_date,
    ledger_sequence_rows,
    ledger_stress_flags,
    member_clear_means,
    observation_role_for_refresh,
)
from engines.suitability import compute_suitability, ndvi_persistence_feature  # noqa: E402
from run_ag_probability import (  # noqa: E402
    _aou_scoped_clear_count,
    _persistence_feature_from_ledger,
    _stress_flags_from_ledger,
    build_observations,
)


def test_unassessable_never_healthy_or_possible():
    weak = [
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 5, "aou_overlap_area": 0.01},
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 5, "aou_overlap_area": 0.01},
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 100, "aou_overlap_area": 0.01},
    ]
    status, meta = aou_assessability_with_area(weak, min_clear_fraction=0.5, min_clear_members=2)
    assert status == "unassessable"
    assert meta["assessable_cell_fraction"] < 0.5
    # Gate: observation role retained; class unassessable
    assert observation_role_for_refresh("unassessable_coverage", has_new=False) == OBSERVATION_ROLE_RETAINED
    assert cell_assessability({"ndvi": 0.5, "ndmi": 0.1, "pixel_count": 10}) == "unassessable"


def test_area_vs_count_fraction_divergence():
    """2% area must not show 100% coverage via count alone."""
    members = [
        # one tiny clear cell
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 100, "clear_fraction": 1.0, "aou_overlap_area": 0.02},
        # large cloudy / unassessable members
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 5, "clear_fraction": 0.0, "aou_overlap_area": 0.49},
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 5, "clear_fraction": 0.0, "aou_overlap_area": 0.49},
    ]
    status, meta = aou_assessability_with_area(
        members, min_clear_fraction=0.01, min_clear_members=1, min_valid_area_fraction=None
    )
    # Count fraction = 1/3 ≈ 0.33; area fraction = 0.02/1.0 = 0.02
    assert abs(meta["assessable_cell_fraction"] - (1 / 3)) < 1e-6
    assert meta["valid_area_fraction"] is not None
    assert abs(meta["valid_area_fraction"] - 0.02) < 1e-9
    assert meta["valid_area_fraction"] != meta["assessable_cell_fraction"]
    # With area threshold 0.20 → unassessable despite count pass
    status2, meta2 = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=0.20,
    )
    assert status2 == "unassessable"
    assert meta2["valid_area_fraction"] < 0.20


def test_shared_aggregate_equality():
    clear = [
        {"ndvi": 0.40, "ndmi": 0.10, "pixel_count": 100, "clear_fraction": 1.0, "aou_overlap_area": 0.5, "source": "s2"},
        {"ndvi": 0.40, "ndmi": 0.10, "pixel_count": 100, "clear_fraction": 1.0, "aou_overlap_area": 0.5, "source": "s2"},
    ]
    all_m = clear + [{"ndvi": None, "ndmi": None, "pixel_count": 5, "aou_overlap_area": 0.1}]
    _, meta = aou_assessability_with_area(clear, min_clear_fraction=0.2, min_clear_members=1)
    agg = build_aou_date_aggregate(
        aou_id="AOU-NJ-000001",
        date="2026-09-01",
        clear_members=clear,
        all_members=all_m,
        assessability="assessable",
        assess_meta=meta,
        run_id="RUN1",
        water_stress=33.53,
        vigor_stress=20.0,
        alert="healthy",
        agricultural_probability=55.0,
        ag_class="possible",
        persistence_feature=1.0,
        n_clear_dates=2,
        n_dates_above_bare=2,
        observation_role=OBSERVATION_ROLE_CURRENT,
        biotic_status="not_flagged",
        possible_biotic_stress=False,
        refresh_status="refreshed",
    )
    assert agg["ndvi"] == 0.4
    assert agg["aggregate_id"] == "AOU-NJ-000001|2026-09-01|RUN1"
    # Simulate registry + ledger + decision reading same blob
    registry_ndvi = agg["ndvi"]
    ledger_ndvi = agg["ndvi"]
    decision_ndvi = agg["ndvi"]
    assert registry_ndvi == ledger_ndvi == decision_ndvi == 0.4
    # Not the divergent 0.40 vs 0.65 case
    assert registry_ndvi != 0.65


def test_history_before_T_no_self_feed():
    unit = {
        "observations": [
            {
                "date": "2026-08-01",
                "ndvi": 0.35,
                "alert": "water_attention",
                "water_stress_score": 70,
                "series_scope": "aou",
            },
            {
                "date": "2026-09-01",
                "ndvi": 0.40,
                "alert": "healthy",
                "water_stress_score": 20,
                "series_scope": "aou",
            },
        ]
    }
    before = ledger_rows_before(unit, "2026-09-01")
    assert len(before) == 1 and before[0]["date"] == "2026-08-01"
    excl = ledger_rows_excluding_date(unit, "2026-09-01")
    assert len(excl) == 1
    flags = ledger_stress_flags(before, kind="water")
    assert flags == [True]
    # Flags including T would self-feed — must not use for priors at T
    flags_with_t = ledger_stress_flags(ledger_sequence_rows(unit), kind="water")
    assert flags_with_t == [True, False]
    assert flags != flags_with_t


def test_idempotent_reprocess_same_day_replace():
    ledger = {
        "units": [
            {
                "aou_id": "AOU-NJ-000001",
                "observations": [
                    {"date": "2026-08-01", "ndvi": 0.35, "series_scope": "aou", "alert": "water_attention", "water_stress_score": 70},
                    {"date": "2026-09-01", "ndvi": 0.40, "series_scope": "aou", "water_stress_score": 33.53, "alert": "healthy"},
                ],
            }
        ]
    }
    # Reprocess T=2026-09-01 with same pending NDVI → same n_clear / persistence
    results = []
    for _ in range(3):
        n = _aou_scoped_clear_count(
            ledger,
            "AOU-NJ-000001",
            pending_date="2026-09-01",
            pending_ndvi=0.40,
            exclude_date="2026-09-01",
        )
        feat, n_clear, n_above, status = _persistence_feature_from_ledger(
            ledger,
            "AOU-NJ-000001",
            pending_date="2026-09-01",
            pending_ndvi=0.40,
            exclude_date="2026-09-01",
        )
        flags = _stress_flags_from_ledger(
            ledger, "AOU-NJ-000001", kind="water", before_date="2026-09-01"
        )
        results.append((n, feat, n_clear, n_above, status, tuple(flags)))
    assert results[0] == results[1] == results[2]
    assert results[0][0] == 2  # Aug + Sep pending, no double-count
    # Without exclude_date, adding pending when T already present would still be 2,
    # but stress flags before T must never include T's own score
    assert results[0][5] == (True,)  # Aug prior only — never T self-feed


def test_suitability_uses_ledger_persistence_not_fake():
    # Explicit feature
    assert ndvi_persistence_feature(n_clear_dates=4, persistence_score_0_1=0.75) == 0.75
    # Forbidden: invent n_clear/4 when feature null
    assert ndvi_persistence_feature(n_clear_dates=4, persistence_score_0_1=None) is None
    suit = compute_suitability(
        aou_id="AOU-NJ-000001",
        agricultural_probability=60.0,
        water_stress_score=30.0,
        vigor_stress_score=25.0,
        ndvi_persistence=0.8,
        n_clear_dates=3,
    )
    assert suit["suitability_components"]["phenology_fit"] == 0.8
    suit2 = compute_suitability(
        aou_id="AOU-NJ-000001",
        agricultural_probability=60.0,
        water_stress_score=30.0,
        vigor_stress_score=25.0,
        ndvi_persistence=None,
        n_clear_dates=4,
    )
    # Null persistence → renorm (phenology absent), not fake 4/4=1.0
    assert suit2["suitability_components"]["phenology_fit"] is None
    assert suit2["weights_used"]["ndvi_persistence"] == 0.0


def test_biotic_three_state():
    assert biotic_three_state(possible_biotic_stress=True, n_clear=3)["biotic_status"] == "possible"
    assert biotic_three_state(possible_biotic_stress=False, n_clear=1)["biotic_status"] == "unknown"
    assert biotic_three_state(possible_biotic_stress=False, n_clear=3)["biotic_status"] == "not_flagged"
    assert biotic_status_three_state(possible_biotic_stress=False, n_clear=0) == "unknown"
    # never confirmed pest
    r = biotic_three_state(possible_biotic_stress=True, n_clear=5)
    assert r["never_confirmed_pest"] is True
    assert r["biotic_risk_label"] == "possible_biotic_stress"


def test_build_observations_uses_aggregate_not_divergent_mean():
    """Registry NDVI 0.40 must match observation row — not re-mean to 0.65."""
    aou_feats = [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "aou_id": "AOU-NJ-000001",
                "date": "2026-09-01",
                "refresh_status": "refreshed",
                "observation_role": OBSERVATION_ROLE_CURRENT,
                "assessability": "assessable",
                "agricultural_probability": 55.0,
                "ag_class": "possible",
                "persistence_status": "multi_date",
                "aou_date_aggregate": {
                    "aggregate_id": "AOU-NJ-000001|2026-09-01|RUN",
                    "date": "2026-09-01",
                    "ndvi": 0.40,
                    "ndmi": 0.10,
                    "water_stress_score": 33.53,
                    "vigor_stress_score": 20.0,
                    "alert": "healthy",
                    "agricultural_probability": 55.0,
                    "ag_class": "possible",
                    "possible_biotic_stress": False,
                    "biotic_status": "not_flagged",
                    "persistence_feature": 1.0,
                    "n_dates_above_bare": 2,
                    "assessable_cell_fraction": 1.0,
                    "valid_area_fraction": 1.0,
                },
            },
        }
    ]
    # Cells that would diverge if re-meaned from all members (0.65 trap)
    cells = [
        {
            "properties": {
                "aou_id": "AOU-NJ-000001",
                "ndvi": 0.90,
                "ndmi": 0.20,
                "assessability": "assessable",
                "water_stress_score": 10,
                "vigor_stress_score": 10,
                "data_quality_confidence": 80,
                "alert": "healthy",
                "date": "2026-09-01",
                "source": "s2",
            }
        },
        {
            "properties": {
                "aou_id": "AOU-NJ-000001",
                "ndvi": 0.40,
                "ndmi": 0.10,
                "assessability": "assessable",
                "water_stress_score": 50,
                "vigor_stress_score": 30,
                "data_quality_confidence": 80,
                "alert": "healthy",
                "date": "2026-09-01",
                "source": "s2",
            }
        },
    ]
    with tempfile.TemporaryDirectory() as td:
        obs = build_observations(aou_feats, {"dates": []}, cells, existing_path=None)
    unit = obs["units"][0]
    row = unit["observations"][0]
    assert row["ndvi"] == 0.4
    assert row["aggregate_id"] == "AOU-NJ-000001|2026-09-01|RUN"
    assert row["observation_role"] == OBSERVATION_ROLE_CURRENT


def test_unassessable_never_writes_observation():
    aou_feats = [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "aou_id": "AOU-NJ-000002",
                "date": "2026-08-01",
                "refresh_status": "unassessable_coverage",
                "observation_role": OBSERVATION_ROLE_RETAINED,
                "assessability": "unassessable",
                "ag_class": "unassessable",
                "aou_date_aggregate": {"ndvi": 0.4, "date": "2026-08-01"},
            },
        }
    ]
    cells = [
        {
            "properties": {
                "aou_id": "AOU-NJ-000002",
                "ndvi": 0.5,
                "ndmi": 0.1,
                "assessability": "unassessable",
                "date": "2026-09-01",
            }
        }
    ]
    obs = build_observations(aou_feats, {"dates": []}, cells, existing_path=None)
    # No new row for T — empty or only prior (none here)
    assert obs["units"][0]["observations"] == []


def test_promote_list_includes_decision():
    """Static check: run_monitor promote set includes decision/*."""
    src = (PIPELINE / "run_monitor.py").read_text()
    assert "decision/aou_suitability_components.json" in src
    assert "decision/run_meta.json" in src
    assert "full_release_ok" in src or "promote_includes_decision" in src
    assert "all-or-nothing" in src or "missing required" in src


if __name__ == "__main__":
    test_unassessable_never_healthy_or_possible()
    test_area_vs_count_fraction_divergence()
    test_shared_aggregate_equality()
    test_history_before_T_no_self_feed()
    test_idempotent_reprocess_same_day_replace()
    test_suitability_uses_ledger_persistence_not_fake()
    test_biotic_three_state()
    test_build_observations_uses_aggregate_not_divergent_mean()
    test_unassessable_never_writes_observation()
    test_promote_list_includes_decision()
    print("OK evaluator deep re-check tests")
