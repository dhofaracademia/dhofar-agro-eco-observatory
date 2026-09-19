#!/usr/bin/env python3
"""Acceptance tests — SCIENCE_LOCKS_v0.4_observation_integrity.md P0."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from shapely.geometry import box, mapping, shape

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

from engines.observation_integrity import (  # noqa: E402
    JOIN_RULE,
    alert_counts_match,
    assign_cells_max_overlap,
    clear_cell_aou_ids,
    count_alerts,
    member_clear_means,
    positive_area_overlap,
    temporal_evidence_labels,
)
from run_ag_probability import (  # noqa: E402
    _aou_scoped_clear_count,
    assign_aou_ids,
    build_observations,
)


def _cell(lon0, lat0, lon1, lat1, *, ndvi, ndmi, date="2026-09-06", alert="healthy", aou_id="STALE"):
    return {
        "type": "Feature",
        "geometry": mapping(box(lon0, lat0, lon1, lat1)),
        "properties": {
            "ndvi": ndvi,
            "ndmi": ndmi,
            "date": date,
            "alert": alert,
            "aou_id": aou_id,
            "pixel_count": 100,
            "cloud_cover": 5.0,
            "source": "test",
            "product_id": "TEST",
            "tile": "39QYA",
        },
    }


def test_positive_area_rejects_touch_only():
    a = box(0, 0, 1, 1)
    b = box(1, 0, 2, 1)  # shares edge only
    assert a.intersects(b)
    assert positive_area_overlap(a, b) == 0.0
    c = box(0.5, 0.5, 1.5, 1.5)
    assert positive_area_overlap(a, c) > 0


def test_clear_stale_and_max_overlap():
    # Two AOUs; cell overlaps both — max overlap wins; touch-only dropped
    cells = [
        _cell(0.0, 0.0, 1.0, 1.0, ndvi=0.4, ndmi=0.1),  # overlaps A heavily, B lightly
        _cell(1.0, 0.0, 2.0, 1.0, ndvi=0.35, ndmi=0.05),  # touch-only with A if A ends at 1.0
    ]
    # Ensure stale IDs present
    assert all(c["properties"]["aou_id"] == "STALE" for c in cells)
    aou_geoms = [
        ("AOU-A", box(0.0, 0.0, 0.9, 1.0)),
        ("AOU-B", box(0.7, 0.0, 1.8, 1.0)),
    ]
    by = assign_cells_max_overlap(cells, aou_geoms, bare_ndvi=0.18)
    assert cells[0]["properties"]["aou_id"] in ("AOU-A", "AOU-B")
    # Cell0 overlap with A = 0.9, with B = 0.2 → A wins
    assert cells[0]["properties"]["aou_id"] == "AOU-A"
    # Cell1: overlap A=0 (touch at x=1), overlap B = 0.8 → B
    assert positive_area_overlap(aou_geoms[0][1], shape(cells[1]["geometry"])) == 0.0
    assert cells[1]["properties"]["aou_id"] == "AOU-B"
    assert JOIN_RULE == "max_overlap_area"
    assert len(by["AOU-A"]["members"]) == 1


def test_mutating_cell_ndvi_changes_aou_score():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reg = {
            "type": "aou_registry",
            "version": "0.4.1",
            "units": [
                {
                    "aou_id": "AOU-NJ-000001",
                    "active": True,
                    "geometry": mapping(box(0, 0, 1, 1)),
                    "centroid_lon": 0.5,
                    "centroid_lat": 0.5,
                    "area_ha_est": 5.0,
                    "ndvi": 0.3,
                    "ndmi": 0.05,
                    "agricultural_probability": 50.0,
                    "ag_class": "possible",
                    "first_seen_date": "2026-08-01",
                    "last_seen_date": "2026-08-01",
                }
            ],
        }
        reg_path = td / "aou_registry.json"
        reg_path.write_text(json.dumps(reg))
        cells = [_cell(0.1, 0.1, 0.9, 0.9, ndvi=0.25, ndmi=0.02, date="2026-09-06")]
        feats, registry, aou_feats, join_meta = assign_aou_ids(
            cells, reg_path, "2026-09-06", ledger=None
        )
        assert join_meta["join_rule"] == "max_overlap_area"
        p1 = aou_feats[0]["properties"]
        assert p1["refresh_status"] == "refreshed"
        assert p1["date"] == "2026-09-06"
        prob1 = p1["agricultural_probability"]

        cells2 = [_cell(0.1, 0.1, 0.9, 0.9, ndvi=0.55, ndmi=0.15, date="2026-09-06")]
        # persist registry from first run
        from engines.aou_identity import save_registry

        save_registry(reg_path, registry)
        feats2, registry2, aou_feats2, _ = assign_aou_ids(
            cells2, reg_path, "2026-09-06", ledger=None
        )
        prob2 = aou_feats2[0]["properties"]["agricultural_probability"]
        assert prob2 is not None and prob1 is not None
        assert prob2 != prob1, (prob1, prob2)


def test_missing_valid_obs_does_not_advance_date():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        reg = {
            "type": "aou_registry",
            "version": "0.4.1",
            "units": [
                {
                    "aou_id": "AOU-NJ-000002",
                    "active": True,
                    "geometry": mapping(box(0, 0, 1, 1)),
                    "centroid_lon": 0.5,
                    "centroid_lat": 0.5,
                    "area_ha_est": 5.0,
                    "ndvi": 0.4,
                    "ndmi": 0.1,
                    "agricultural_probability": 62.0,
                    "ag_class": "possible",
                    "first_seen_date": "2026-08-01",
                    "last_seen_date": "2026-08-01",
                }
            ],
        }
        reg_path = td / "aou_registry.json"
        reg_path.write_text(json.dumps(reg))
        # Cells far away — no positive overlap
        cells = [_cell(10, 10, 11, 11, ndvi=0.5, ndmi=0.2, date="2026-09-06")]
        _, registry, aou_feats, _ = assign_aou_ids(cells, reg_path, "2026-09-06", ledger=None)
        p = aou_feats[0]["properties"]
        assert p["refresh_status"] in ("stale", "no_new_observation")
        assert p["last_seen_date"] == "2026-08-01"
        assert p["date"] == "2026-08-01"
        assert p["agricultural_probability"] == 62.0
        assert registry["units"][0]["last_seen_date"] == "2026-08-01"


def test_rerun_stale_keeps_prior_date_in_ledger():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        obs_path = td / "aou_observations.json"
        prior = {
            "units": [
                {
                    "aou_id": "AOU-NJ-000003",
                    "n_clear_dates": 1,
                    "observations": [
                        {
                            "aou_id": "AOU-NJ-000003",
                            "date": "2026-08-01",
                            "ndvi": 0.4,
                            "ndmi": 0.1,
                            "agricultural_probability": 60.0,
                            "ag_class": "possible",
                            "series_scope": "aou_members_aggregate",
                        }
                    ],
                }
            ]
        }
        obs_path.write_text(json.dumps(prior))
        aou_feats = [
            {
                "type": "Feature",
                "geometry": mapping(box(0, 0, 1, 1)),
                "properties": {
                    "aou_id": "AOU-NJ-000003",
                    "date": "2026-08-01",
                    "refresh_status": "no_new_observation",
                    "agricultural_probability": 60.0,
                    "ag_class": "possible",
                },
            }
        ]
        # No members assigned → should not upsert 2026-09-06
        out = build_observations(aou_feats, {"dates": []}, [], existing_path=obs_path)
        dates = [o["date"] for o in out["units"][0]["observations"]]
        assert dates == ["2026-08-01"]
        assert "2026-09-06" not in dates


def test_alert_counts_unify():
    feats = [
        _cell(0, 0, 0.1, 0.1, ndvi=0.1, ndmi=0.0, alert="bare"),
        _cell(0.1, 0, 0.2, 0.1, ndvi=0.4, ndmi=0.1, alert="healthy"),
        _cell(0.2, 0, 0.3, 0.1, ndvi=0.3, ndmi=-0.1, alert="water_attention"),
    ]
    # Fix alerts in props (helper sets them)
    feats[0]["properties"]["alert"] = "bare"
    feats[1]["properties"]["alert"] = "healthy"
    feats[2]["properties"]["alert"] = "water_attention"
    a = count_alerts(feats)
    b = {"bare": 1, "healthy": 1, "water_attention": 1}
    assert alert_counts_match(a, b)
    assert not alert_counts_match(a, {"bare": 1, "healthy": 2})


def test_temporal_evidence_insufficient_ar():
    te = temporal_evidence_labels(1)
    assert te["temporal_evidence_sufficient"] is False
    assert te["temporal_evidence_ar"] == "أدلة زمنية غير كافية"
    assert te["biotic_unknown_reason"] == "insufficient_temporal_evidence"
    te2 = temporal_evidence_labels(2)
    assert te2["temporal_evidence_sufficient"] is True


def test_ledger_n_clear_not_window():
    ledger = {
        "units": [
            {
                "aou_id": "AOU-X",
                "observations": [
                    {"date": "2026-08-01", "ndvi": 0.3, "series_scope": "aou_members_aggregate"},
                    {"date": "2026-08-01", "ndvi": 0.3, "series_scope": "window_not_aou"},
                ],
            }
        ]
    }
    assert _aou_scoped_clear_count(ledger, "AOU-X") == 1
    assert _aou_scoped_clear_count(ledger, "AOU-X", pending_date="2026-09-06", pending_ndvi=0.4) == 2


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    if failed:
        sys.exit(1)
    print(f"OK — {len(tests)} acceptance tests")
