#!/usr/bin/env python3
"""Post-#29 evaluator residuals — R3-1 / R3-2 / R3-3 (SCIENCE_LOCKS_v0.4_post29)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engines.biotic import biotic_three_state, infer_biotic_from_cell
from engines.observation_integrity import (
    DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
    aou_assessability_with_area,
    atomic_promote_with_rollback,
)


def test_r3_1_clear_pixel_area_fraction_not_full_polygon():
    """50/2500 clear (clear_fraction=0.02), positive overlap → ~0.02; fail gate at 0.20.

    Must NOT report valid_area_fraction=1.0 from full accepted-cell polygon.
    """
    members = [
        {
            "ndvi": 0.40,
            "ndmi": 0.10,
            "pixel_count": 50,
            "clear_fraction": 0.02,
            "aou_overlap_area": 1.0,
            "scl_clear": True,
        }
    ]
    status, meta = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=None,
    )
    assert meta["valid_area_fraction_basis"] in ("clear_pixels_in_aou", "overlap_times_clear_fraction_estimate")
    assert meta["valid_area_fraction"] is not None
    assert abs(meta["valid_area_fraction"] - 0.02) < 1e-9, meta["valid_area_fraction"]
    # Full-polygon numerator would have been 1.0 — forbidden
    assert meta["valid_area_fraction"] != 1.0
    assert meta["clear_overlap_area_sum"] == 1.0  # diagnostic only

    status2, meta2 = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=0.20,
    )
    assert status2 == "unassessable"
    assert meta2["valid_area_fraction"] < 0.20
    assert meta2["min_valid_area_fraction_aou"] == DEFAULT_MIN_VALID_AREA_FRACTION_AOU


def test_r3_1_round2_area_vs_count_still_diverges():
    """Regression: tiny clear overlap vs large cloudy members → area 0.02 ≠ count.

    R4-1 requires clear_fraction present for numerator; cloudy members use low fraction.
    """
    members = [
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 100, "clear_fraction": 1.0, "aou_overlap_area": 0.02},
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 5, "clear_fraction": 0.0, "aou_overlap_area": 0.49},
        {"ndvi": 0.4, "ndmi": 0.1, "pixel_count": 5, "clear_fraction": 0.0, "aou_overlap_area": 0.49},
    ]
    _, meta = aou_assessability_with_area(
        members, min_clear_fraction=0.01, min_clear_members=1, min_valid_area_fraction=None
    )
    assert abs(meta["valid_area_fraction"] - 0.02) < 1e-9
    assert meta["valid_area_fraction_basis"] in (
        "clear_pixels_in_aou",
        "overlap_times_clear_fraction_estimate",
    )


def test_r3_2_infer_possible_via_pipeline_path():
    """Case where infer alone returns possible must be possible after ledger re-infer."""
    # Two prior vigor flags True + current high vigor / spatial anomaly → persistence ok
    prior = [True, True]
    biotic = infer_biotic_from_cell(
        ndvi=0.15,
        ndmi=0.05,
        ndvi_p25=0.30,
        ndmi_p25=-0.05,
        vigor_stress=70.0,
        water_stress=20.0,
        neighbor_ndvi_median=0.35,
        data_quality_confidence=80.0,
        prior_vigor_flags=prior,
    )
    assert biotic["possible_biotic_stress"] is True
    # Full-pipeline three-state with rules_evaluated after ledger priors
    b3 = biotic_three_state(
        possible_biotic_stress=True,
        n_clear=3,
        rules_evaluated=True,
    )
    assert b3["biotic_status"] == "possible"


def test_r3_2_silence_is_unknown_not_not_flagged():
    """Insufficient evidence / silence → unknown, never not_flagged."""
    assert (
        biotic_three_state(
            possible_biotic_stress=False, n_clear=1, rules_evaluated=False
        )["biotic_status"]
        == "unknown"
    )
    assert (
        biotic_three_state(
            possible_biotic_stress=False, n_clear=3, rules_evaluated=False
        )["biotic_status"]
        == "unknown"
    )
    # not_flagged only when rules actually evaluated with ledger-backed inputs
    assert (
        biotic_three_state(
            possible_biotic_stress=False, n_clear=3, rules_evaluated=True
        )["biotic_status"]
        == "not_flagged"
    )


def test_r3_2_empty_prior_flags_infer_not_possible():
    """Empty priors cannot clear persistence alone — aligns with silence≠not_flagged."""
    biotic = infer_biotic_from_cell(
        ndvi=0.15,
        ndmi=0.05,
        ndvi_p25=0.30,
        ndmi_p25=-0.05,
        vigor_stress=70.0,
        water_stress=20.0,
        neighbor_ndvi_median=0.35,
        data_quality_confidence=80.0,
        prior_vigor_flags=[],
    )
    assert biotic["possible_biotic_stress"] is False
    assert biotic["rules"]["persistence_ge_2"] is False


def test_r3_3_promote_fail_after_third_restores_last_good():
    """Inject fail on 3rd move → prior public set fully intact (no half-update)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public = root / "public"
        stage = root / "stage"
        public.mkdir()
        stage.mkdir()
        # Last-good public contents
        files = [
            "latest_alerts.geojson",
            "timeseries.json",
            "aou/aou_observations.json",
            "meta/run_meta.json",
            "decision/run_meta.json",
        ]
        for rel in files:
            p = public / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"version": "last_good", "path": rel}))
            s = stage / rel
            s.parent.mkdir(parents=True, exist_ok=True)
            s.write_text(json.dumps({"version": "new", "path": rel}))

        try:
            atomic_promote_with_rollback(
                stage_root=stage,
                public_root=public,
                relative_paths=files,
                fail_after=3,
            )
            raise AssertionError("expected promote to fail")
        except RuntimeError as e:
            assert "injected promote failure" in str(e)

        for rel in files:
            doc = json.loads((public / rel).read_text())
            assert doc["version"] == "last_good", f"{rel} was not restored: {doc}"


def test_r3_3_promote_success_replaces_all():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public = root / "public"
        stage = root / "stage"
        public.mkdir()
        stage.mkdir()
        files = ["latest_alerts.geojson", "timeseries.json", "meta/run_meta.json"]
        for rel in files:
            (public / rel).parent.mkdir(parents=True, exist_ok=True)
            (public / rel).write_text('{"version":"old"}')
            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
            (stage / rel).write_text('{"version":"new"}')
        atomic_promote_with_rollback(
            stage_root=stage, public_root=public, relative_paths=files
        )
        for rel in files:
            assert json.loads((public / rel).read_text())["version"] == "new"


def main():
    test_r3_1_clear_pixel_area_fraction_not_full_polygon()
    test_r3_1_round2_area_vs_count_still_diverges()
    test_r3_2_infer_possible_via_pipeline_path()
    test_r3_2_silence_is_unknown_not_not_flagged()
    test_r3_2_empty_prior_flags_infer_not_possible()
    test_r3_3_promote_fail_after_third_restores_last_good()
    test_r3_3_promote_success_replaces_all()
    print("test_post29_residuals: OK")


if __name__ == "__main__":
    main()
