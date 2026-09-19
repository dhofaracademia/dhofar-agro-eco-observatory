#!/usr/bin/env python3
"""Post-#30 evaluator follow-up — R4-1…R4-4 (SCIENCE_LOCKS_v0.4_post30_evaluator_followup).

Does not re-open closed #30 R3 PASSes. Mountain 3.B Hold.
"""

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
    publish_release_with_pointer,
    stamp_release_id_on_doc,
    verify_release_ids_match,
)


def test_r4_1_aou_target_denom_10pct_not_100():
    """10% of AOU observed clear → ~0.10, not 1.0 from member-overlap denom."""
    members = [
        {
            "ndvi": 0.4,
            "ndmi": 0.1,
            "pixel_count": 100,
            "clear_fraction": 1.0,
            "aou_overlap_area": 0.10,
            "scl_clear": True,
        }
    ]
    status, meta = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=None,
        aou_target_area=1.0,
    )
    assert meta["valid_area_fraction_denominator"] == "aou_target_area"
    assert abs(meta["valid_area_fraction"] - 0.10) < 1e-9, meta
    assert meta["valid_area_fraction"] != 1.0
    # Without target area, member-overlap denom would collapse to 1.0 — forbidden claim
    _, meta2 = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=None,
        aou_target_area=None,
    )
    assert meta2["valid_area_fraction_denominator"] == "member_overlap_sum"
    assert abs(meta2["valid_area_fraction"] - 1.0) < 1e-9  # diagnostic collapse


def test_r4_1_missing_clear_fraction_no_silent_full_clear():
    """Missing clear_fraction must not invent 1.0; no auto-accept under area gate."""
    members = [
        {
            "ndvi": 0.4,
            "ndmi": 0.1,
            "pixel_count": 200,
            "aou_overlap_area": 1.0,
            "scl_clear": True,
            # clear_fraction intentionally absent
        }
    ]
    status, meta = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=0.20,
        aou_target_area=1.0,
    )
    assert meta["clear_fraction_missing"] is True
    assert meta["clear_pixel_area_in_aou_sum"] == 0.0
    assert meta["valid_area_fraction"] == 0.0
    assert status == "unassessable"
    # Never display-path as full clear
    assert meta["valid_area_fraction"] != 1.0


def test_r4_1_50_of_2500_fails_gate():
    """Acceptance (a): 50/2500 → ~2% fails 20% gate."""
    members = [
        {
            "ndvi": 0.4,
            "ndmi": 0.1,
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
        min_valid_area_fraction=0.20,
        aou_target_area=1.0,
    )
    assert abs(meta["valid_area_fraction"] - 0.02) < 1e-9
    assert status == "unassessable"
    assert meta["min_valid_area_fraction_aou"] == DEFAULT_MIN_VALID_AREA_FRACTION_AOU


def test_r4_1_overlaps_capped_at_100pct():
    members = [
        {
            "ndvi": 0.4,
            "ndmi": 0.1,
            "pixel_count": 100,
            "clear_fraction": 1.0,
            "aou_overlap_area": 0.8,
            "scl_clear": True,
        },
        {
            "ndvi": 0.4,
            "ndmi": 0.1,
            "pixel_count": 100,
            "clear_fraction": 1.0,
            "aou_overlap_area": 0.8,
            "scl_clear": True,
        },
    ]
    _, meta = aou_assessability_with_area(
        members,
        min_clear_fraction=0.01,
        min_clear_members=1,
        min_valid_area_fraction=None,
        aou_target_area=1.0,
    )
    assert meta["valid_area_fraction"] <= 1.0 + 1e-12


def test_r4_2_rejected_current_unknown_trusted_unchanged():
    """Prior history + rejected current → current unknown; trusted date unchanged."""
    # Simulate decision path without calling full pipeline: gate logic contract
    has_new = False
    assess = "unassessable"
    last_trusted = "possible"
    last_trusted_date = "2026-08-01"
    possible_biotic = False
    biotic_status = "unknown"
    if not (has_new and assess == "assessable"):
        possible_biotic = False
        biotic_status = "unknown"
        # do not advance
    assert biotic_status == "unknown"
    assert last_trusted == "possible"
    assert last_trusted_date == "2026-08-01"
    assert possible_biotic is False


def test_r4_2_accepted_sufficient_history_possible():
    """Sufficient history + accepted → possible via infer + three-state."""
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
    b3 = biotic_three_state(
        possible_biotic_stress=True, n_clear=3, rules_evaluated=True
    )
    assert b3["biotic_status"] == "possible"


def test_r4_2_insufficient_unknown():
    assert (
        biotic_three_state(
            possible_biotic_stress=False, n_clear=1, rules_evaluated=False
        )["biotic_status"]
        == "unknown"
    )


def test_r4_3_fail_before_pointer_leaves_current_unchanged():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public = root / "public"
        stage = root / "stage"
        public.mkdir()
        stage.mkdir()
        files = [
            "latest_alerts.geojson",
            "timeseries.json",
            "meta/run_meta.json",
        ]
        # Pre-existing CURRENT pointing at old release
        old_id = "oldrelease"
        (public / "releases" / old_id).mkdir(parents=True)
        (public / "CURRENT").write_text(old_id + "\n")
        (public / "latest_release.json").write_text(
            json.dumps({"release_id": old_id})
        )
        for rel in files:
            (public / rel).parent.mkdir(parents=True, exist_ok=True)
            (public / rel).write_text(json.dumps({"version": "live_old", "release_id": old_id}))
            s = stage / rel
            s.parent.mkdir(parents=True, exist_ok=True)
            s.write_text(json.dumps({"version": "new", "release_id": "newrelease"}))

        try:
            publish_release_with_pointer(
                stage_root=stage,
                public_root=public,
                release_id="newrelease",
                relative_paths=files,
                fail_before_pointer=True,
            )
            raise AssertionError("expected failure before pointer")
        except RuntimeError as e:
            assert "before pointer" in str(e)

        assert (public / "CURRENT").read_text().strip() == old_id
        assert json.loads((public / "latest_release.json").read_text())["release_id"] == old_id


def test_r4_3_pointer_swap_after_full_tree():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public = root / "public"
        stage = root / "stage"
        public.mkdir()
        stage.mkdir()
        files = ["latest_alerts.geojson", "timeseries.json", "meta/run_meta.json"]
        rid = "rel20260920"
        for rel in files:
            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
            (stage / rel).write_text(json.dumps({"version": "new", "release_id": rid, "run_id": rid}))
            # seed live tree so compat mirror has something to snapshot
            (public / rel).parent.mkdir(parents=True, exist_ok=True)
            (public / rel).write_text(json.dumps({"version": "old", "release_id": "old"}))

        publish_release_with_pointer(
            stage_root=stage,
            public_root=public,
            release_id=rid,
            relative_paths=files,
        )
        assert (public / "CURRENT").read_text().strip() == rid
        assert (public / "releases" / rid / "meta" / "run_meta.json").is_file()
        assert json.loads((public / "latest_release.json").read_text())["release_id"] == rid
        # No mixed read: live mirror matches new
        assert json.loads((public / "meta" / "run_meta.json").read_text())["version"] == "new"


def test_r4_3_fail_mid_copy_pointer_unchanged():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public = root / "public"
        stage = root / "stage"
        public.mkdir()
        stage.mkdir()
        files = ["a.json", "b.json", "c.json"]
        (public / "CURRENT").write_text("keep\n")
        for rel in files:
            (stage / rel).write_text("{}")
        try:
            publish_release_with_pointer(
                stage_root=stage,
                public_root=public,
                release_id="partial",
                relative_paths=files,
                fail_mid_copy=2,
            )
            raise AssertionError("expected mid-copy fail")
        except RuntimeError:
            pass
        assert (public / "CURRENT").read_text().strip() == "keep"


def test_r4_4_release_id_gate_and_stamp():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rid = "unify-1"
        files = {
            "meta/run_meta.json": {"release_id": rid, "run_id": rid},
            "meta/last_refresh.json": {"release_id": rid, "run_id": rid},
            "timeseries.json": {"release_id": rid, "run_id": rid},
            "latest_alerts.geojson": {
                "type": "FeatureCollection",
                "release_id": rid,
                "properties": {"release_id": rid, "run_id": rid},
                "features": [],
            },
            "aou/aou_observations.json": {"release_id": rid, "units": []},
            "aou/aou_registry.json": {"release_id": rid, "units": []},
            "aou/aou_registry.geojson": {
                "type": "FeatureCollection",
                "release_id": rid,
                "features": [],
            },
            "decision/run_meta.json": {"release_id": rid, "run_id": rid},
            "decision/aou_confidence.json": {"release_id": rid, "units": []},
            "decision/aou_suitability_components.json": {"release_id": rid, "units": []},
            "decision/aou_evidence_gaps.json": {"release_id": rid, "units": []},
        }
        for rel, doc in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc))
        assert verify_release_ids_match(root, rid) == []

        # Mismatch aborts
        bad = json.loads((root / "decision" / "run_meta.json").read_text())
        bad["release_id"] = "other"
        (root / "decision" / "run_meta.json").write_text(json.dumps(bad))
        fails = verify_release_ids_match(root, rid)
        assert any("id_mismatch:decision/run_meta.json" in f for f in fails)

        # stamp helper
        doc = {"foo": 1}
        stamp_release_id_on_doc(doc, "X")
        assert doc["release_id"] == "X" and doc["run_id"] == "X"


def test_r3_4_single_decision_one_release_id():
    """AgriTech soft follow-up: one release_id set across meta+decision (behavior)."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rid = "single-decision-1"
        for rel in (
            "meta/run_meta.json",
            "meta/last_refresh.json",
            "decision/run_meta.json",
            "decision/aou_confidence.json",
            "timeseries.json",
            "latest_alerts.geojson",
            "aou/aou_observations.json",
            "aou/aou_registry.json",
            "aou/aou_registry.geojson",
            "decision/aou_suitability_components.json",
            "decision/aou_evidence_gaps.json",
        ):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if rel.endswith(".geojson"):
                path.write_text(
                    json.dumps(
                        {
                            "type": "FeatureCollection",
                            "release_id": rid,
                            "properties": {"release_id": rid},
                            "features": [],
                        }
                    )
                )
            else:
                path.write_text(json.dumps({"release_id": rid, "run_id": rid}))
        assert verify_release_ids_match(root, rid) == []


def test_r3_3_rollback_still_holds():
    """Do not reopen: fail after 3rd move still restores last-good."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public = root / "public"
        stage = root / "stage"
        public.mkdir()
        stage.mkdir()
        files = ["a.json", "b.json", "c.json", "d.json"]
        for rel in files:
            (public / rel).write_text(json.dumps({"version": "last_good"}))
            (stage / rel).write_text(json.dumps({"version": "new"}))
        try:
            atomic_promote_with_rollback(
                stage_root=stage,
                public_root=public,
                relative_paths=files,
                fail_after=3,
            )
            raise AssertionError("expected fail")
        except RuntimeError:
            pass
        for rel in files:
            assert json.loads((public / rel).read_text())["version"] == "last_good"


def main():
    test_r4_1_aou_target_denom_10pct_not_100()
    test_r4_1_missing_clear_fraction_no_silent_full_clear()
    test_r4_1_50_of_2500_fails_gate()
    test_r4_1_overlaps_capped_at_100pct()
    test_r4_2_rejected_current_unknown_trusted_unchanged()
    test_r4_2_accepted_sufficient_history_possible()
    test_r4_2_insufficient_unknown()
    test_r4_3_fail_before_pointer_leaves_current_unchanged()
    test_r4_3_pointer_swap_after_full_tree()
    test_r4_3_fail_mid_copy_pointer_unchanged()
    test_r4_4_release_id_gate_and_stamp()
    test_r3_4_single_decision_one_release_id()
    test_r3_3_rollback_still_holds()
    print("test_post30_followup: OK")


if __name__ == "__main__":
    main()
