#!/usr/bin/env python3
"""v0.4 Phase-1 Agricultural Probability + AOU identity + stress + biotic.

Modes:
  1) Offline enrich (default): read existing latest_alerts.geojson + timeseries.json,
     apply SCIENCE_LOCKS formulas, segment AOUs, write aou_registry / observations,
     and rewrite latest_alerts with new fields (ndre null if unavailable).
  2) Called after run_monitor.py full STAC path (same writers).

Cite: docs/SCIENCE_LOCKS_v0.4_phase1_2.md + SCIENCE_LOCKS_v0.4_evaluator_endorsement.md + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + SCIENCE_LOCKS_v0.4_observation_integrity.md + SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md + SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md + SCIENCE_LOCKS_v0.4_evaluator_round2.md
AOU ≠ farm; DQ ≠ ecological confidence; biotic ≠ pest certainty.
500 m grid remains fallback/debug (geometry_kind=monitoring_grid_500m).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

from engines.ag_probability import agricultural_probability  # noqa: E402
from engines.aou_identity import (  # noqa: E402
    load_registry,
    mint_or_match_aou,
    save_registry,
    segment_probability_mask
)
from engines.observation_integrity import (  # noqa: E402
    DEFAULT_MIN_CLEAR_FRACTION_AOU,
    DEFAULT_MIN_CLEAR_FRACTION_CELL,
    DEFAULT_MIN_CLEAR_MEMBERS_AOU,
    DEFAULT_MIN_CLEAR_PIXELS_CELL,
    DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
    DISCOVERY_ESTABLISHED,
    DISCOVERY_PROVISIONAL,
    JOIN_RULE,
    OBSERVATION_ROLE_CURRENT,
    OBSERVATION_ROLE_RETAINED,
    cap_ag_class_for_discovery,
    discovery_status_for_n_clear,
    alert_counts_match,
    aou_assessability_with_area,
    assign_cells_max_overlap,
    biotic_status_three_state,
    build_aou_date_aggregate,
    cell_assessability,
    count_alerts,
    ledger_persistence_feature,
    ledger_rows_before,
    ledger_rows_excluding_date,
    ledger_sequence_rows,
    ledger_stress_flags,
    member_clear_means,
    observation_role_for_refresh,
    positive_area_overlap,
    temporal_evidence_labels,
    atomic_promote_with_rollback,
    aou_geometry_target_area,
    publish_release_with_pointer,
    verify_release_ids_match,
    stamp_release_id_on_doc
)
from engines.biotic import biotic_three_state, infer_biotic_from_cell  # noqa: E402
from engines.stress import (  # noqa: E402
    map_stress_to_alert,
    vigor_stress_score,
    water_stress_score
)

BARE_NDVI = 0.18
EXPECTED_PIXELS = 2500

# Published formula_ref (lock §B / post-integrity evaluator)
FORMULA_REF_POST = (
    "SCIENCE_LOCKS_v0.4_phase1_2.md + "
    "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
    "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
    "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md + "
    "SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md + "
    "SCIENCE_LOCKS_v0.4_post29_evaluator_residuals.md"
)
FORMULA_REF_AOU = (
    "SCIENCE_LOCKS_v0.4_phase1_2.md§1-2 + "
    "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
    "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
    "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md + "
    "SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md + "
    "SCIENCE_LOCKS_v0.4_post29_evaluator_residuals.md"
)


def out_data_dir() -> Path:
    import os

    return Path(os.environ.get("MONITOR_OUT_DATA", str(REPO_ROOT / "app" / "public" / "data")))


def data_quality_confidence(cloud_cover: float | None, pixel_count: int | None) -> float:
    cloud = float(cloud_cover) if cloud_cover is not None else 0.0
    cloud_score = max(0.0, 100.0 - cloud * 4.0)
    valid_fraction = min(1.0, (pixel_count or EXPECTED_PIXELS * 0.5) / EXPECTED_PIXELS)
    score = 0.4 * cloud_score + 0.6 * (valid_fraction * 100.0)
    return round(max(5.0, min(97.0, score)), 1)


CLEAR_FRACTION_BASIS_PROVIDED = "provided"
CLEAR_FRACTION_BASIS_VALID_TOTAL = "valid_pixel_count_over_total_pixel_count"
CLEAR_FRACTION_BASIS_PIXEL_EXPECTED = "pixel_count_over_expected_grid"
CLEAR_FRACTION_BASIS_MISSING = "missing"


def ensure_cell_clear_fraction(props: dict) -> dict:
    """Carry or reconstruct cell clear_fraction for R4-1 (offline enrich).

    Prefer existing clear_fraction. Else valid/total if both present.
    Else pixel_count / EXPECTED_PIXELS with honest basis stamp.
    Never invent silent 1.0 without a basis stamp.
    """
    if props.get("clear_fraction") is not None:
        try:
            props["clear_fraction"] = round(max(0.0, min(1.0, float(props["clear_fraction"]))), 6)
        except (TypeError, ValueError):
            props["clear_fraction"] = None
        else:
            if not props.get("clear_fraction_basis"):
                props["clear_fraction_basis"] = CLEAR_FRACTION_BASIS_PROVIDED
            return props
    vpc = props.get("valid_pixel_count")
    tpc = props.get("total_pixel_count")
    try:
        if vpc is not None and tpc is not None and float(tpc) > 0:
            props["clear_fraction"] = round(min(1.0, max(0.0, float(vpc) / float(tpc))), 6)
            props["clear_fraction_basis"] = CLEAR_FRACTION_BASIS_VALID_TOTAL
            return props
    except (TypeError, ValueError):
        pass
    pc = props.get("pixel_count")
    try:
        if pc is not None and EXPECTED_PIXELS > 0:
            props["clear_fraction"] = round(
                min(1.0, max(0.0, float(pc) / float(EXPECTED_PIXELS))), 6
            )
            props["clear_fraction_basis"] = CLEAR_FRACTION_BASIS_PIXEL_EXPECTED
            props.setdefault("total_pixel_count", int(EXPECTED_PIXELS))
            props.setdefault("valid_pixel_count", int(pc))
            return props
    except (TypeError, ValueError):
        pass
    props["clear_fraction"] = None
    props["clear_fraction_basis"] = CLEAR_FRACTION_BASIS_MISSING
    return props


def cell_key(props: dict) -> str:
    # Stable debug key only — NOT AOU identity (SCIENCE_LOCKS §2.2)
    return f"grid:{props.get('date')}:{round(props.get('ndvi', 0), 4)}:{round(props.get('ndmi', 0), 4)}:{props.get('pixel_count')}"


def enrich_features(features: list[dict], *, month: int | None) -> list[dict]:
    """Apply AgProb + stress + biotic to monitoring-grid features.

    n_clear_dates is per-cell / AOU-scoped SCL-clear count — NEVER the
    AOI timeseries window length (SCIENCE_LOCKS evaluator endorsement).
    Offline enrich starts at n_clear_dates=1 per cell; AOU n_clear comes
    from the temporal ledger (multi-date when ledger has multiple dates).
    Stress calls use stress_flags_recent=[] here (renorm/null). After AOU
    assign, multi-date units (n_clear≥2) re-score via ledger flags.
    R4-1: reconstruct clear_fraction from pixel_count/valid/total when
    SCL fraction absent so AOU valid_area_fraction is not a universal 0.
    """
    # Neighbor NDVI medians for biotic spatial term (simple peer p25 fallback)
    veg_ndvi = [
        f["properties"]["ndvi"]
        for f in features
        if f["properties"].get("ndvi") is not None and f["properties"]["ndvi"] >= BARE_NDVI
    ]
    peer_ndvi_med = None
    if veg_ndvi:
        s = sorted(veg_ndvi)
        peer_ndvi_med = s[len(s) // 2]

    out = []
    for f in features:
        p = dict(f["properties"])
        ndvi = p.get("ndvi")
        ndmi = p.get("ndmi")
        if ndvi is None or ndmi is None:
            out.append(f)
            continue

        # NDRE unavailable on offline grid enrich path
        ndre = p.get("ndre")
        ndre_available = bool(p.get("ndre_available", False) and ndre is not None)
        if not ndre_available:
            p["ndre"] = None
            p["ndre_available"] = False
            p["ndre_status"] = "unavailable"
            p["ndre_band"] = None

        # Cell-scoped clear dates only. No multi-date cell history offline → 1.
        # FORBIDDEN: len(timeseries.dates) / window length as n_clear_dates.
        n_clear_dates = 1
        n_above = 1 if ndvi >= BARE_NDVI else 0
        persistence_estimated = False  # window must never raise class alone
        persistence_gate = False  # requires AOU/cell n_clear >= 2

        swir_feature = p.get("swir_feature")
        ag = agricultural_probability(
            ndvi=ndvi,
            ndmi=ndmi,
            ndre=ndre if ndre_available else None,
            ndre_available=ndre_available,
            n_clear_dates=n_clear_dates,
            n_dates_above_bare=n_above,
            month=month,
            local_variance=None,
            swir_feature=swir_feature if swir_feature is not None else None,
        )
        if swir_feature is not None:
            p["swir_source"] = p.get("swir_source", "b11_b12")
        elif "swir_source" not in p:
            p["swir_source"] = "proxy_ndvi_ndmi"
        p["agricultural_probability"] = ag["agricultural_probability"]
        p["ag_class"] = ag["ag_class"]
        p["ag_probability_status"] = "expert_v1"
        p["n_clear_dates"] = n_clear_dates
        p["n_dates_above_bare"] = n_above
        p["persistence_status"] = ag.get("persistence_status", "single_date_insufficient")
        p["persistence_gate"] = False
        p["persistence_estimated_from_window"] = persistence_estimated
        p["formula_ref_ag"] = ag["formula_ref"]

        dq = data_quality_confidence(p.get("cloud_cover"), p.get("pixel_count"))
        p["data_quality_confidence"] = dq

        water = water_stress_score(
            ndmi=ndmi,
            ndmi_p25_veg=p.get("ndmi_p25_veg", -0.05),
            ndmi_p50_veg=None,
            ndmi_hist_median=None,  # renorm weights when no history
            stress_flags_recent=[],
            month=month,
            ndvi=ndvi,
            n_clear_dates=n_clear_dates,
        )
        vigor = vigor_stress_score(
            ndvi=ndvi,
            ndvi_p25_veg=p.get("ndvi_p25_veg", 0.25),
            ndvi_p50_veg=None,
            ndvi_hist_median=None,
            ndre=ndre if ndre_available else None,
            stress_flags_recent=[],
            month=month,
            n_clear_dates=n_clear_dates,
        )
        p["water_stress_score"] = water["water_stress_score"]
        p["vigor_stress_score"] = vigor["vigor_stress_score"]
        p["stress_components_water"] = water["components"]
        p["stress_components_vigor"] = vigor["components"]
        p["stress_status"] = "expert_v1"
        p["formula_ref_stress"] = water["formula_ref"]

        alert = map_stress_to_alert(
            ndvi=ndvi,
            bare_floor=BARE_NDVI,
            water=water,
            vigor=vigor,
            data_quality_confidence=dq,
        )
        p["alert"] = alert
        p["geometry_kind"] = "monitoring_grid_500m"

        # R4-1: carry/reconstruct clear_fraction before cell/AOU area gates
        ensure_cell_clear_fraction(p)

        # Pre-gate assessability BEFORE final alert/ag_class publish (deep re-check §1)
        p["assessability"] = cell_assessability(
            p,
            min_clear_pixels=DEFAULT_MIN_CLEAR_PIXELS_CELL,
            min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_CELL,
        )
        biotic = infer_biotic_from_cell(
            ndvi=ndvi,
            ndmi=ndmi,
            ndvi_p25=p.get("ndvi_p25_veg", 0.25),
            ndmi_p25=p.get("ndmi_p25_veg", -0.05),
            vigor_stress=vigor["vigor_stress_score"],
            water_stress=water["water_stress_score"],
            neighbor_ndvi_median=peer_ndvi_med,
            data_quality_confidence=dq,
            prior_vigor_flags=[],
        )
        p["possible_biotic_stress"] = biotic["possible_biotic_stress"]
        p["biotic_disclaimer_en"] = biotic["disclaimer_en"]
        p["biotic_disclaimer_ar"] = biotic["disclaimer_ar"]
        # Empty stress/biotic history ≠ "no biotic issue"
        te = temporal_evidence_labels(n_clear_dates)
        for k, v in te.items():
            p[k] = v
        b3 = biotic_three_state(
            possible_biotic_stress=bool(biotic["possible_biotic_stress"]),
            n_clear=n_clear_dates,
            rules_evaluated=True,
        )
        p["biotic_status"] = b3["biotic_status"]
        if b3["biotic_status"] == "unknown":
            p["biotic_unknown_reason"] = "insufficient_temporal_evidence"
        if p["assessability"] == "unassessable":
            # Never map unassessable → healthy / possible|likely|very_likely
            p["alert"] = "unclear"
            p["ag_class"] = "unassessable"
            p["observation_role"] = "unassessable"
        else:
            p["observation_role"] = OBSERVATION_ROLE_CURRENT

        out.append({"type": "Feature", "geometry": f["geometry"], "properties": p})
    return out


def _load_observations_ledger(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _ledger_dates_for_aou(ledger: dict[str, Any] | None, aou_id: str) -> set[str]:
    """Distinct AOU-scoped clear dates from the ledger (never window_not_aou)."""
    dates: set[str] = set()
    if not ledger:
        return dates
    for unit in ledger.get("units") or []:
        if unit.get("aou_id") != aou_id:
            continue
        for o in unit.get("observations") or []:
            if o.get("series_scope") == "window_not_aou":
                continue
            if o.get("date") and o.get("ndvi") is not None:
                dates.add(str(o["date"]))
    return dates


def _aou_scoped_clear_count(
    ledger: dict[str, Any] | None,
    aou_id: str,
    *,
    pending_date: str | None = None,
    pending_ndvi: float | None = None,
    exclude_date: str | None = None
) -> int:
    """Distinct ledger dates where series_scope != window_not_aou.

    Forbidden sources: first_seen/last_seen alone; hardcoded 1/4; window length.
    exclude_date: drop same-day T before optionally adding pending (idempotent replace).
    Optional pending_* includes today's clear row about to be upserted (documented).
    """
    dates = _ledger_dates_for_aou(ledger, aou_id)
    if exclude_date:
        dates.discard(str(exclude_date))
    if pending_date and pending_ndvi is not None:
        dates.add(str(pending_date))
    return len(dates)




def _unit_from_ledger(ledger: dict[str, Any] | None, aou_id: str) -> dict[str, Any] | None:
    if not ledger:
        return None
    for unit in ledger.get("units") or []:
        if unit.get("aou_id") == aou_id:
            return unit
    return None


def _persistence_feature_from_ledger(
    ledger: dict[str, Any] | None,
    aou_id: str,
    *,
    pending_ndvi: float | None = None,
    pending_date: str | None = None,
    exclude_date: str | None = None
) -> tuple[float | None, int, int, str]:
    """Ledger-sequence persistence only — never invent 0.5 from n_clear>=2 alone.

    Same-day replace: exclude_date drops T from prior sequence before pending upsert
    so reprocess of T does not double-count or self-feed.
    """
    unit = _unit_from_ledger(ledger, aou_id)
    rows = ledger_rows_excluding_date(unit, exclude_date or pending_date)
    if pending_date and pending_ndvi is not None:
        rows = list(rows) + [{"date": str(pending_date), "ndvi": float(pending_ndvi)}]
        rows.sort(key=lambda r: str(r["date"]))
    feat, n_clear, n_above = ledger_persistence_feature(rows, bare_ndvi=BARE_NDVI)
    from engines.ag_probability import persistence_status as _ps
    status = _ps(n_clear)
    if n_clear >= 2 and feat is None:
        status = "insufficient_sequence"
    return feat, n_clear, n_above, status



def _rescore_stress_with_ledger_flags(
    props: dict,
    *,
    water_flags: list[bool],
    vigor_flags: list[bool],
    month: int | None,
    n_clear_dates: int
) -> None:
    """Feed ledger stress_flags into water/vigor scores when n_clear≥2.

    While n_clear < 2, keep empty-flag renorm/null persistence path.
    Mutates props in place (shared with Feature.properties for members).
    """
    ndvi = props.get("ndvi")
    ndmi = props.get("ndmi")
    if ndvi is None or ndmi is None:
        return
    # Single-date / insufficient sequence → empty flags (renorm), not invented healthy
    use_flags = n_clear_dates >= 2
    w_flags = list(water_flags) if use_flags else []
    v_flags = list(vigor_flags) if use_flags else []
    ndre = props.get("ndre")
    ndre_available = bool(props.get("ndre_available", False) and ndre is not None)
    water = water_stress_score(
        ndmi=ndmi,
        ndmi_p25_veg=props.get("ndmi_p25_veg", -0.05),
        ndmi_p50_veg=None,
        ndmi_hist_median=None,
        stress_flags_recent=w_flags,
        month=month,
        ndvi=ndvi,
        n_clear_dates=n_clear_dates,
    )
    vigor = vigor_stress_score(
        ndvi=ndvi,
        ndvi_p25_veg=props.get("ndvi_p25_veg", 0.25),
        ndvi_p50_veg=None,
        ndvi_hist_median=None,
        ndre=ndre if ndre_available else None,
        stress_flags_recent=v_flags,
        month=month,
        n_clear_dates=n_clear_dates,
    )
    props["water_stress_score"] = water["water_stress_score"]
    props["vigor_stress_score"] = vigor["vigor_stress_score"]
    props["stress_components_water"] = water["components"]
    props["stress_components_vigor"] = vigor["components"]
    props["stress_status"] = "expert_v1"
    props["formula_ref_stress"] = water["formula_ref"]
    props["stress_flags_recent_water"] = w_flags
    props["stress_flags_recent_vigor"] = v_flags
    if use_flags:
        # AOU-scoped multi-date evidence for stress persistence term
        props["n_clear_dates"] = n_clear_dates
    dq = props.get("data_quality_confidence")
    if dq is None:
        dq = data_quality_confidence(props.get("cloud_cover"), props.get("pixel_count"))
        props["data_quality_confidence"] = dq
    props["alert"] = map_stress_to_alert(
        ndvi=ndvi,
        bare_floor=BARE_NDVI,
        water=water,
        vigor=vigor,
        data_quality_confidence=dq,
    )


def _stress_flags_from_ledger(
    ledger: dict[str, Any] | None,
    aou_id: str,
    *,
    kind: str,
    before_date: str | None = None
) -> list[bool]:
    """Prior stress flags from history strictly before T — never self-feed date T.

    Empty flags mean renorm — never 'no stress / healthy'.
    """
    unit = _unit_from_ledger(ledger, aou_id)
    rows = ledger_rows_before(unit, before_date) if before_date else ledger_sequence_rows(unit)
    return ledger_stress_flags(rows, kind=kind)

def _current_detection_for_run(
    *,
    intersecting: list[dict],
    vegetated: list[dict],
    ag_class: str | None
) -> str:
    """detected | weak | not_detected — orthogonal to registry active identity."""
    possible_plus = {"possible", "likely", "very_likely"}
    if vegetated or (ag_class in possible_plus and intersecting):
        return "detected"
    if intersecting:
        return "weak"
    return "not_detected"


def _sync_registry_from_ledger(
    registry: dict[str, Any],
    aou_features: list[dict],
    obs_doc: dict[str, Any]
) -> None:
    """n_clear + first_seen/last_seen from ledger; re-gate ag_class/persistence.

    Deep re-check: must NOT promote unassessable → current ag class
    (possible|likely|very_likely). Retained last-good scores keep observation_role.
    """
    from engines.ag_probability import ag_class_from_probability, persistence_status

    by_id = {u["aou_id"]: u for u in obs_doc.get("units") or []}
    forbidden_promote = {"possible", "likely", "very_likely", "healthy"}

    def _gate_class(assess: str | None, proposed: str | None, prior: str | None) -> str | None:
        if assess == "unassessable":
            # Never invent a healthy/possible class from ledger sync
            if proposed in forbidden_promote or proposed is None:
                return "unassessable"
            if prior == "unassessable" or prior is None:
                return "unassessable"
            # Keep prior class only as retained chrome, but stamp unassessable for current
            return "unassessable"
        return proposed

    for rec in registry.get("units") or []:
        aid = rec.get("aou_id")
        unit = by_id.get(aid) or {}
        dates = sorted(_ledger_dates_for_aou({"units": [unit]}, aid))
        n_clear = len(dates)
        rec["n_clear_dates"] = n_clear
        if dates:
            rec["first_seen_date"] = dates[0]
            # last_seen_date advances only via assign_aou_ids when refreshed;
            # sync may align from ledger max date when assessable current
            if rec.get("assessability") != "unassessable" or rec.get("refresh_status") == "refreshed":
                rec["last_seen_date"] = dates[-1]
        rows = ledger_sequence_rows(unit)
        pers_feat, n_seq, n_above = ledger_persistence_feature(rows, bare_ndvi=BARE_NDVI)
        rec["n_dates_above_bare"] = n_above
        rec["persistence_feature"] = pers_feat  # None when sequence insufficient
        assess = rec.get("assessability")
        prob = rec.get("agricultural_probability")
        if assess == "unassessable":
            rec["ag_class"] = "unassessable"
            if rec.get("observation_role") != OBSERVATION_ROLE_CURRENT:
                rec["observation_role"] = OBSERVATION_ROLE_RETAINED
        elif prob is not None:
            proposed = ag_class_from_probability(
                float(prob),
                n_clear_dates=n_clear,
                persistence_feature=0.0 if pers_feat is None else float(pers_feat),
                single_date_only=n_clear < 2,
            )
            rec["ag_class"] = _gate_class(assess, proposed, rec.get("ag_class"))
        rec["persistence_status"] = persistence_status(n_clear) if n_clear < 2 else (
            persistence_status(n_clear) if pers_feat is not None else "insufficient_sequence"
        )

    for feat in aou_features:
        p = feat["properties"]
        aid = p.get("aou_id")
        unit = by_id.get(aid) or {}
        dates = sorted(_ledger_dates_for_aou({"units": [unit]}, aid))
        n_clear = len(dates)
        p["n_clear_dates"] = n_clear
        if dates:
            p["first_seen_date"] = dates[0]
            if p.get("assessability") != "unassessable" or p.get("refresh_status") == "refreshed":
                p["last_seen_date"] = dates[-1]
        if unit.get("n_clear_dates") is not None:
            p["n_clear_dates"] = int(unit["n_clear_dates"])
            n_clear = int(unit["n_clear_dates"])
        rows = ledger_sequence_rows(unit)
        pers_feat, n_seq, n_above = ledger_persistence_feature(rows, bare_ndvi=BARE_NDVI)
        p["n_dates_above_bare"] = n_above
        p["persistence_feature"] = pers_feat
        assess = p.get("assessability")
        if assess == "unassessable":
            p["ag_class"] = "unassessable"
            if p.get("observation_role") != OBSERVATION_ROLE_CURRENT:
                p["observation_role"] = OBSERVATION_ROLE_RETAINED
        else:
            prob = p.get("agricultural_probability")
            if prob is not None:
                proposed = ag_class_from_probability(
                    float(prob),
                    n_clear_dates=n_clear,
                    persistence_feature=0.0 if pers_feat is None else float(pers_feat),
                    single_date_only=n_clear < 2,
                )
                p["ag_class"] = _gate_class(assess, proposed, p.get("ag_class"))
        p["persistence_status"] = persistence_status(n_clear) if (n_clear < 2 or pers_feat is not None) else "insufficient_sequence"


def assign_aou_ids(
    features: list[dict],
    registry_json_path: Path,
    observation_date: str,
    ledger: dict[str, Any] | None = None
) -> tuple[list[dict], dict[str, Any], list[dict], dict[str, Any]]:
    """Persistent AOUs with integrity-pack join + refresh rules.

    - Clear stale cell→AOU; positive-area overlap only; multi-hit → max_overlap_area.
    - Scores from **current** in-AOU cell NDVI/NDMI. No valid new clear sample →
      do NOT advance observation_date / last_seen_date; stamp refresh_status=stale.
    - n_clear from AOU observation ledger (append/upsert elsewhere).
    """
    from engines.ag_probability import (
        ag_class_from_probability,
        agricultural_probability,
        persistence_status,
    )

    registry = load_registry(registry_json_path)
    aou_features: list[dict] = []
    active = [u for u in (registry.get("units") or []) if u.get("active", True) and u.get("geometry")]
    join_meta = {
        "join_rule": JOIN_RULE,
        "join_predicate": "positive_area_overlap",
        "formula_ref": "SCIENCE_LOCKS_v0.4_observation_integrity.md§1 + SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md",
    }

    def _honest_class(
        prob: float | None,
        n_clear: int,
        persistence_feature: float | None = None,
    ) -> str | None:
        if prob is None:
            return None
        # Forbidden: invent 0.5 solely from n_clear>=2 without ledger sequence
        pers = 0.0 if persistence_feature is None else float(persistence_feature)
        return ag_class_from_probability(
            float(prob),
            n_clear_dates=n_clear,
            persistence_feature=pers,
            single_date_only=n_clear < 2,
        )

    def _score_unit_from_ndvi_ndmi(
        ndvi, ndmi, month: int | None, n_clear: int, n_dates_above_bare: int | None = None
    ) -> dict:
        if ndvi is None or ndmi is None:
            return {"agricultural_probability": None, "ag_class": None, "persistence_status": persistence_status(n_clear)}
        n_above = (
            int(n_dates_above_bare)
            if n_dates_above_bare is not None
            else (1 if float(ndvi) >= BARE_NDVI else 0)
        )
        ag = agricultural_probability(
            ndvi=float(ndvi),
            ndmi=float(ndmi),
            n_clear_dates=n_clear,
            n_dates_above_bare=n_above,
            month=month,
        )
        return {
            "agricultural_probability": ag["agricultural_probability"],
            "ag_class": ag["ag_class"],
            "persistence_status": ag.get("persistence_status", persistence_status(n_clear)),
            "n_dates_above_bare": n_above,
        }

    month = None
    if observation_date:
        try:
            month = int(str(observation_date).split("-")[1])
        except Exception:
            month = None


    def _discover_mint_from_features(cell_feats: list[dict], *, allow_unassigned_only: bool) -> None:
        """Round-2 R2-3: mint/match new AOUs with provisional_new until n_clear>=2.

        Never mint from unassessable coverage. Day-1 max ag_class=possible.
        When allow_unassigned_only, only cells without an aou_id are considered.
        """
        nonlocal aou_features
        pool = list(cell_feats)
        if allow_unassigned_only:
            pool = [
                f
                for f in cell_feats
                if not f.get("properties", {}).get("aou_id")
            ]
        if not pool:
            return
        candidates = segment_probability_mask(pool)
        if not candidates:
            return
        cand_geoms = [(f"__cand_{i}", c["geometry"]) for i, c in enumerate(candidates)]
        by_cand = assign_cells_max_overlap(pool, cand_geoms, bare_ndvi=BARE_NDVI)
        for i, cand in enumerate(candidates):
            cand_key = f"__cand_{i}"
            cand_members = (by_cand.get(cand_key) or {}).get("members") or []
            for m in cand_members:
                m["assessability"] = cell_assessability(
                    m,
                    min_clear_pixels=DEFAULT_MIN_CLEAR_PIXELS_CELL,
                    min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_CELL,
                )
            cand_target = aou_geometry_target_area(shape(cand["geometry"])) if cand.get("geometry") else None
            if cand_target is None:
                try:
                    cand_target = float(shape(cand["geometry"]).area)
                except Exception:
                    cand_target = None
            assess_c, assess_meta_c = aou_assessability_with_area(
                cand_members,
                min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_AOU,
                min_clear_members=DEFAULT_MIN_CLEAR_MEMBERS_AOU,
                min_valid_area_fraction=DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
                aou_target_area=cand_target,
            )
            if assess_c == "unassessable" or not cand_members:
                continue
            clear_c = [m for m in cand_members if m.get("assessability") == "assessable"]
            mean_ndvi, mean_ndmi = member_clear_means(clear_c)
            if mean_ndvi is None or mean_ndmi is None:
                continue
            scored = _score_unit_from_ndvi_ndmi(mean_ndvi, mean_ndmi, month, 1)
            ag_class = scored["ag_class"] or _honest_class(scored["agricultural_probability"], 1)
            ag_class = cap_ag_class_for_discovery(
                ag_class, n_clear=1, discovery_status=DISCOVERY_PROVISIONAL
            )
            props = {
                "agricultural_probability": scored["agricultural_probability"],
                "ag_class": ag_class,
                "area_ha_est": cand["area_ha_est"],
                "n_clear_dates": 1,
                "persistence_status": persistence_status(1),
                "discovery_status": DISCOVERY_PROVISIONAL,
            }
            aou_id, rec = mint_or_match_aou(
                cand["geometry"],
                registry,
                observation_date=observation_date or "1970-01-01",
                props=props,
            )
            for mi in (by_cand.get(cand_key) or {}).get("member_indices") or []:
                pool[mi]["properties"]["aou_id"] = aou_id
            n_ledger = _aou_scoped_clear_count(
                ledger,
                aou_id,
                pending_date=observation_date,
                pending_ndvi=mean_ndvi,
                exclude_date=observation_date,
            )
            disc = discovery_status_for_n_clear(n_ledger)
            ag_class = cap_ag_class_for_discovery(
                ag_class, n_clear=n_ledger, discovery_status=disc
            )
            te = temporal_evidence_labels(n_ledger)
            rec["ndvi"] = round(float(mean_ndvi), 4)
            rec["ndmi"] = round(float(mean_ndmi), 4)
            rec["current_detection"] = "detected" if mean_ndvi >= BARE_NDVI else "weak"
            rec["n_clear_dates"] = n_ledger
            rec["refresh_status"] = "refreshed"
            rec["active"] = True
            rec["discovery_status"] = disc
            rec["discovery_action"] = rec.get("discovery_action") or "mint"
            rec["ag_class"] = ag_class
            rec["assessability"] = "assessable"
            rec["valid_area_fraction"] = assess_meta_c.get("valid_area_fraction")
            rec["assessable_cell_fraction"] = assess_meta_c.get("assessable_cell_fraction")
            for k, v in te.items():
                rec[k] = v
            if any(f["properties"].get("aou_id") == aou_id for f in aou_features):
                continue
            aou_features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(cand["geometry"]),
                    "properties": {
                        "aou_id": aou_id,
                        "previous_ids": rec.get("previous_ids", []),
                        "first_seen_date": rec.get("first_seen_date"),
                        "last_seen_date": rec.get("last_seen_date"),
                        "active": True,
                        "current_detection": rec["current_detection"],
                        "refresh_status": "refreshed",
                        "observation_role": OBSERVATION_ROLE_CURRENT,
                        "agricultural_probability": props["agricultural_probability"],
                        "ag_class": ag_class,
                        "area_ha_est": cand["area_ha_est"],
                        "ndvi": rec.get("ndvi"),
                        "ndmi": rec.get("ndmi"),
                        "ndre": None,
                        "ndre_available": False,
                        "ndre_status": "unavailable",
                        "member_count": cand["member_count"],
                        "geometry_kind": "aou_segment",
                        "aou_not_official_farm": True,
                        "n_clear_dates": n_ledger,
                        "persistence_status": props["persistence_status"],
                        "persistence_feature": None,
                        "persistence_estimated_from_window": False,
                        "assessability": "assessable",
                        "assessable_cell_fraction": assess_meta_c.get("assessable_cell_fraction"),
                        "valid_area_fraction": assess_meta_c.get("valid_area_fraction"),
                        "valid_area_fraction_basis": assess_meta_c.get("valid_area_fraction_basis"),
                        "valid_area_fraction_denominator": assess_meta_c.get("valid_area_fraction_denominator"),
                        "discovery_status": disc,
                        "discovery_action": rec.get("discovery_action"),
                        "match_iou": rec.get("match_iou"),
                        "evidence_level": "satellite_only",
                        "product_stamp": "provisional_satellite_analytical_service",
                        "najd_model_validation": "not_validated",
                        "formula_ref": FORMULA_REF_AOU,
                        "date": observation_date,
                        "join_rule": JOIN_RULE,
                        **te,
                    },
                }
            )


    if active:
        aou_geoms: list[tuple[str, Any]] = []
        rec_by_id: dict[str, dict] = {}
        for rec in active:
            try:
                geom = shape(rec["geometry"])
            except Exception:
                continue
            aou_geoms.append((rec["aou_id"], geom))
            rec_by_id[rec["aou_id"]] = rec

        by_aou = assign_cells_max_overlap(features, aou_geoms, bare_ndvi=BARE_NDVI)

        for aou_id, geom in aou_geoms:
            rec = rec_by_id[aou_id]
            bucket = by_aou.get(aou_id) or {"members": [], "vegetated": []}
            members = bucket["members"]
            vegetated = bucket["vegetated"]
            # Per-cell assessability BEFORE aggregate / scoring / observation write
            for m in members:
                m["assessability"] = cell_assessability(
                    m,
                    min_clear_pixels=DEFAULT_MIN_CLEAR_PIXELS_CELL,
                    min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_CELL,
                )
            aou_target = aou_geometry_target_area(geom, area_ha_est=rec.get("area_ha_est"))
            assess, assess_meta = aou_assessability_with_area(
                members,
                min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_AOU,
                min_clear_members=DEFAULT_MIN_CLEAR_MEMBERS_AOU,
                min_valid_area_fraction=DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
                aou_target_area=aou_target,
            )
            clear_members = [m for m in members if m.get("assessability") == "assessable"]
            mean_ndvi, mean_ndmi = member_clear_means(clear_members)

            has_new = assess == "assessable" and mean_ndvi is not None and mean_ndmi is not None
            pending_ndvi = mean_ndvi if has_new else None
            # Idempotent reprocess: exclude same-day T from prior, then add pending
            n_clear = _aou_scoped_clear_count(
                ledger,
                aou_id,
                pending_date=observation_date if has_new else None,
                pending_ndvi=pending_ndvi,
                exclude_date=observation_date,
            )
            pers_feat, _ns, n_above, pers_stat = _persistence_feature_from_ledger(
                ledger,
                aou_id,
                pending_ndvi=pending_ndvi,
                pending_date=observation_date if has_new else None,
                exclude_date=observation_date,
            )
            # Prior stress flags: history strictly before T (never self-feed T)
            water_flags = _stress_flags_from_ledger(
                ledger, aou_id, kind="water", before_date=observation_date
            )
            vigor_flags = _stress_flags_from_ledger(
                ledger, aou_id, kind="vigor", before_date=observation_date
            )
            # Stress recalc ONLY on clear_members (not cloudy/unassessable cells)
            if n_clear >= 2 and clear_members:
                for m in clear_members:
                    _rescore_stress_with_ledger_flags(
                        m,
                        water_flags=water_flags,
                        vigor_flags=vigor_flags,
                        month=month,
                        n_clear_dates=n_clear,
                    )
            te = temporal_evidence_labels(n_clear)

            last_good_ndvi = rec.get("ndvi")
            last_good_ndmi = rec.get("ndmi")
            last_good_date = rec.get("last_seen_date")
            last_good_prob = rec.get("agricultural_probability")
            last_good_class = rec.get("ag_class")

            if not members:
                refresh_status = "no_new_observation"
                mean_prob = last_good_prob
                ag_class = last_good_class
                if ag_class in ("possible", "likely", "very_likely") and assess == "unassessable":
                    ag_class = "unassessable"
                pers_status = pers_stat or persistence_status(n_clear)
                stamp_date = last_good_date
                out_ndvi, out_ndmi = last_good_ndvi, last_good_ndmi
                obs_role = OBSERVATION_ROLE_RETAINED
            elif assess == "unassessable":
                # Unassessable: never create/advance observation; keep last-good ≠ current
                refresh_status = "unassessable_coverage"
                mean_prob = last_good_prob
                ag_class = "unassessable"
                pers_status = pers_stat or persistence_status(n_clear)
                stamp_date = last_good_date
                out_ndvi, out_ndmi = last_good_ndvi, last_good_ndmi
                obs_role = OBSERVATION_ROLE_RETAINED
            elif has_new:
                scored = _score_unit_from_ndvi_ndmi(
                    mean_ndvi, mean_ndmi, month, n_clear, n_dates_above_bare=n_above
                )
                mean_prob = scored["agricultural_probability"]
                ag_class = scored["ag_class"] or _honest_class(mean_prob, n_clear, pers_feat)
                pers_status = pers_stat or scored.get("persistence_status") or persistence_status(n_clear)
                refresh_status = "refreshed"
                stamp_date = observation_date
                rec["ndvi"] = round(mean_ndvi, 4)
                rec["ndmi"] = round(mean_ndmi, 4)
                rec["last_seen_date"] = observation_date
                out_ndvi, out_ndmi = rec["ndvi"], rec["ndmi"]
                obs_role = OBSERVATION_ROLE_CURRENT
            else:
                refresh_status = "stale" if (last_good_ndvi is None or last_good_ndmi is None) else "no_new_observation"
                mean_prob = last_good_prob
                ag_class = last_good_class or _honest_class(mean_prob, n_clear, pers_feat)
                pers_status = pers_stat or persistence_status(n_clear)
                stamp_date = last_good_date
                out_ndvi, out_ndmi = last_good_ndvi, last_good_ndmi
                obs_role = OBSERVATION_ROLE_RETAINED

            # R3-2 + R4-2: re-infer biotic AFTER ledger history + final water/vigor.
            # Current biotic ONLY when has_new AND assessability=assessable.
            # Rejected / unassessable / retained → current unknown; last-trusted separate.
            last_trusted_biotic = rec.get("biotic_status_last_trusted") or rec.get("biotic_status")
            last_trusted_biotic_date = rec.get("biotic_last_trusted_date") or rec.get("last_seen_date")
            possible_biotic = False
            rules_evaluated = False
            biotic_status = "unknown"
            if has_new and assess == "assessable" and clear_members and n_clear >= 2 and len(vigor_flags) >= 1:
                rules_evaluated = True
                for m in clear_members:
                    if m.get("ndvi") is None or m.get("ndmi") is None:
                        continue
                    cur_vigor = bool(
                        m.get("alert") == "vigor_attention"
                        or (
                            m.get("vigor_stress_score") is not None
                            and float(m["vigor_stress_score"]) >= 55.0
                        )
                    )
                    flags = list(vigor_flags) + [cur_vigor]
                    dq = m.get("data_quality_confidence")
                    if dq is None:
                        dq = 50.0
                    biotic = infer_biotic_from_cell(
                        ndvi=float(m["ndvi"]),
                        ndmi=float(m["ndmi"]),
                        ndvi_p25=m.get("ndvi_p25_veg", 0.25),
                        ndmi_p25=m.get("ndmi_p25_veg", -0.05),
                        vigor_stress=float(m.get("vigor_stress_score") or 0),
                        water_stress=float(m.get("water_stress_score") or 0),
                        neighbor_ndvi_median=m.get("peer_ndvi_median"),
                        data_quality_confidence=float(dq),
                        prior_vigor_flags=flags,
                    )
                    m["possible_biotic_stress"] = biotic["possible_biotic_stress"]
                    m["biotic_disclaimer_en"] = biotic["disclaimer_en"]
                    m["biotic_disclaimer_ar"] = biotic["disclaimer_ar"]
                    m["biotic_rules"] = biotic.get("rules")
                    if biotic["possible_biotic_stress"]:
                        possible_biotic = True
                b3 = biotic_three_state(
                    possible_biotic_stress=possible_biotic,
                    n_clear=n_clear,
                    rules_evaluated=rules_evaluated,
                )
                biotic_status = b3["biotic_status"]
                # Accepted current → advance last-trusted biotic
                last_trusted_biotic = biotic_status
                last_trusted_biotic_date = observation_date
            else:
                # Rejected / retained / insufficient → current unknown; do not emit possible
                possible_biotic = False
                biotic_status = "unknown"
                for m in clear_members or []:
                    m["possible_biotic_stress"] = False
                # Do not advance last-trusted biotic date

            detection = _current_detection_for_run(
                intersecting=members,
                vegetated=vegetated,
                ag_class=ag_class if assess == "assessable" else None,
            )
            member_count = len(vegetated) or len(members) or rec.get("member_count")

            w_score = (
                round(
                    sum(m.get("water_stress_score") or 0 for m in clear_members) / max(1, len(clear_members)),
                    2,
                )
                if clear_members
                else None
            )
            v_score = (
                round(
                    sum(m.get("vigor_stress_score") or 0 for m in clear_members) / max(1, len(clear_members)),
                    2,
                )
                if clear_members
                else None
            )
            if clear_members:
                alerts = [m.get("alert") for m in clear_members]
                agg_alert = max(set(alerts), key=alerts.count) if alerts else "unclear"
            else:
                agg_alert = None

            # Single (AOU, date) aggregate blob — registry / ledger / decision share this
            agg = build_aou_date_aggregate(
                aou_id=aou_id,
                date=stamp_date if obs_role == OBSERVATION_ROLE_RETAINED else (observation_date if has_new else stamp_date),
                clear_members=clear_members,
                all_members=members,
                assessability=assess,
                assess_meta=assess_meta,
                run_id=None,
                water_stress=w_score,
                vigor_stress=v_score,
                alert=agg_alert,
                agricultural_probability=mean_prob if has_new else last_good_prob,
                ag_class=ag_class,
                persistence_feature=pers_feat,
                n_clear_dates=n_clear,
                n_dates_above_bare=n_above,
                observation_role=obs_role,
                biotic_status=biotic_status,
                possible_biotic_stress=possible_biotic,
                refresh_status=refresh_status,
            )
            # For current observation, NDVI/NDMI on aggregate are from clear_members
            if has_new:
                agg["ndvi"] = out_ndvi
                agg["ndmi"] = out_ndmi
                agg["date"] = observation_date
                agg["agricultural_probability"] = mean_prob
            else:
                # Retained last-good: stamp prior values; do not pretend current means
                agg["ndvi"] = out_ndvi
                agg["ndmi"] = out_ndmi
                agg["date"] = stamp_date
                agg["agricultural_probability"] = mean_prob
                agg["last_good_date"] = last_good_date

            rec["agricultural_probability"] = mean_prob
            rec["ag_class"] = ag_class
            rec["n_clear_dates"] = n_clear
            rec["n_dates_above_bare"] = n_above
            rec["persistence_feature"] = pers_feat
            rec["persistence_status"] = pers_status
            rec["current_detection"] = detection
            rec["refresh_status"] = refresh_status
            rec["assessability"] = assess
            rec["assessability_meta"] = assess_meta
            rec["assessable_cell_fraction"] = assess_meta.get("assessable_cell_fraction")
            rec["valid_area_fraction"] = assess_meta.get("valid_area_fraction")
            rec["observation_role"] = obs_role
            rec["discovery_status"] = discovery_status_for_n_clear(n_clear)
            ag_class = cap_ag_class_for_discovery(
                ag_class, n_clear=n_clear, discovery_status=rec["discovery_status"]
            )
            rec["ag_class"] = ag_class
            rec["biotic_status"] = biotic_status
            rec["possible_biotic_stress"] = possible_biotic
            rec["biotic_status_last_trusted"] = last_trusted_biotic
            rec["biotic_last_trusted_date"] = last_trusted_biotic_date
            rec["aggregate_id"] = agg["aggregate_id"]
            rec["aou_date_aggregate"] = agg
            rec["last_good_date"] = last_good_date
            rec["last_good_ndvi"] = last_good_ndvi
            rec["last_good_ndmi"] = last_good_ndmi
            rec["stress_flags_recent_water"] = water_flags
            rec["stress_flags_recent_vigor"] = vigor_flags
            rec["active"] = True if rec.get("active", True) else False
            for k, v in te.items():
                rec[k] = v

            aou_features.append(
                {
                    "type": "Feature",
                    "geometry": rec["geometry"],
                    "properties": {
                        "aou_id": aou_id,
                        "previous_ids": rec.get("previous_ids", []),
                        "first_seen_date": rec.get("first_seen_date"),
                        "last_seen_date": rec.get("last_seen_date"),
                        "active": bool(rec.get("active", True)),
                        "current_detection": detection,
                        "refresh_status": refresh_status,
                        "observation_role": obs_role,
                        "agricultural_probability": mean_prob,
                        "ag_class": ag_class,
                        "area_ha_est": rec.get("area_ha_est"),
                        "ndvi": out_ndvi,
                        "ndmi": out_ndmi,
                        "ndre": None,
                        "ndre_available": False,
                        "ndre_status": "unavailable",
                        "member_count": member_count,
                        "geometry_kind": "aou_segment",
                        "aou_not_official_farm": True,
                        "n_clear_dates": n_clear,
                        "n_dates_above_bare": n_above,
                        "persistence_feature": pers_feat,
                        "persistence_status": pers_status,
                        "persistence_estimated_from_window": False,
                        "assessability": assess,
                        "clear_member_count": assess_meta.get("clear_member_count"),
                        "clear_fraction": assess_meta.get("clear_fraction"),
                        "assessable_cell_fraction": assess_meta.get("assessable_cell_fraction"),
                        "valid_area_fraction": assess_meta.get("valid_area_fraction"),
                        "stress_flags_recent_water": water_flags,
                        "stress_flags_recent_vigor": vigor_flags,
                        "water_stress_score": w_score,
                        "vigor_stress_score": v_score,
                        "alert": agg_alert,
                        "possible_biotic_stress": possible_biotic,
                        "biotic_status": biotic_status,
                        "biotic_status_last_trusted": last_trusted_biotic,
                        "biotic_last_trusted_date": last_trusted_biotic_date,
                        "valid_area_fraction_basis": assess_meta.get("valid_area_fraction_basis"),
                        "valid_area_fraction_denominator": assess_meta.get("valid_area_fraction_denominator"),
                        "clear_fraction_missing": assess_meta.get("clear_fraction_missing"),
                        "aou_target_area": assess_meta.get("aou_target_area"),
                        "discovery_status": rec.get("discovery_status"),
                        "discovery_action": rec.get("discovery_action"),
                        "match_iou": rec.get("match_iou"),
                        "aggregate_id": agg["aggregate_id"],
                        "aou_date_aggregate": agg,
                        "last_good_date": last_good_date,
                        "evidence_level": "satellite_only",
                        "product_stamp": "provisional_satellite_analytical_service",
                        "najd_model_validation": "not_validated",
                        "formula_ref": FORMULA_REF_AOU,
                        "date": stamp_date,
                        "join_rule": JOIN_RULE,
                        **te,
                    },
                }
            )

        # Round-2 R2-3: discover NEW AOUs after registry non-empty
        _discover_mint_from_features(features, allow_unassigned_only=True)

    else:
        # Cold start — same discovery policy (provisional_new, no unassessable mint)
        _discover_mint_from_features(features, allow_unassigned_only=False)

    # Ensure every cell has explicit aou_id (None if unassigned)
    for f in features:
        f["properties"].setdefault("aou_id", None)

    return features, registry, aou_features, join_meta



def build_observations(
    aou_features: list[dict],
    timeseries: dict[str, Any],
    enriched_cells: list[dict],
    existing_path: Path | None = None
) -> dict[str, Any]:
    """Per-AOU ledger: load + append/upsert by (aou_id, date). Never wipe to latest-only.

    observations[] = AOU-scoped clear rows only (never window_not_aou).
    window_context_series rewritten from timeseries as context only.
    n_clear_dates lives on the unit — not as a constant on every row.
    """
    existing_by_aou: dict[str, dict] = {}
    if existing_path is not None and existing_path.exists():
        try:
            prev = json.loads(existing_path.read_text())
            for u in prev.get("units") or []:
                if u.get("aou_id"):
                    existing_by_aou[str(u["aou_id"])] = u
        except Exception:
            existing_by_aou = {}

    by_aou_cells: dict[str, list] = defaultdict(list)
    for f in enriched_cells:
        aid = f["properties"].get("aou_id")
        if aid:
            by_aou_cells[aid].append(f["properties"])

    units = []
    for feat in aou_features:
        p = feat["properties"]
        aid = p["aou_id"]
        members = by_aou_cells.get(aid, [])

        # Keep prior ledger rows (exclude any accidental window rows)
        prior_rows: list[dict] = []
        prev_unit = existing_by_aou.get(aid) or {}
        for o in prev_unit.get("observations") or []:
            if o.get("series_scope") == "window_not_aou":
                continue
            if o.get("date"):
                prior_rows.append(dict(o))
                # Drop misleading per-row constant if present
                prior_rows[-1].pop("n_clear_dates", None)

        by_date: dict[str, dict] = {
            str(o["date"]): o for o in prior_rows if o.get("date")
        }

        # Upsert only when refreshed + assessable + current_observation.
        # Unassessable / retained_last_good → never write a clear observation for T.
        # Consume the SAME aou_date_aggregate blob (no divergent re-mean).
        refresh_status = p.get("refresh_status") or "refreshed"
        obs_role = p.get("observation_role")
        assess = p.get("assessability")
        agg = p.get("aou_date_aggregate") or {}
        if (
            members
            and refresh_status == "refreshed"
            and assess == "assessable"
            and obs_role == OBSERVATION_ROLE_CURRENT
        ):
            clear_ok = [
                m for m in members
                if m.get("assessability") == "assessable"
                and m.get("ndvi") is not None
                and m.get("ndmi") is not None
            ]
            # Prefer shared aggregate NDVI/NDMI; fall back to clear_members mean
            ndvi = agg.get("ndvi")
            ndmi = agg.get("ndmi")
            if (ndvi is None or ndmi is None) and clear_ok:
                ndvi, ndmi = member_clear_means(clear_ok)
            if clear_ok and ndvi is not None and ndmi is not None:
                w = agg.get("water_stress_score")
                if w is None:
                    w = sum(m.get("water_stress_score") or 0 for m in clear_ok) / max(1, len(clear_ok))
                v = agg.get("vigor_stress_score")
                if v is None:
                    v = sum(m.get("vigor_stress_score") or 0 for m in clear_ok) / max(1, len(clear_ok))
                dq = sum(m.get("data_quality_confidence") or 0 for m in clear_ok) / max(1, len(clear_ok))
                biotic = bool(agg.get("possible_biotic_stress")) if "possible_biotic_stress" in agg else any(
                    m.get("possible_biotic_stress") for m in clear_ok
                )
                alert = agg.get("alert")
                if not alert:
                    alerts = [m.get("alert") for m in clear_ok]
                    alert = max(set(alerts), key=alerts.count) if alerts else "unclear"
                obs_date = agg.get("date") or p.get("date") or clear_ok[0].get("date")
                if obs_date:
                    # Same-day replace: overwrite by_date[T] without treating prior T as evidence
                    row = {
                        "aou_id": aid,
                        "date": str(obs_date),
                        "ndvi": round(float(ndvi), 4),
                        "ndmi": round(float(ndmi), 4),
                        "ndre": None,
                        "ndre_available": False,
                        "agricultural_probability": agg.get("agricultural_probability", p.get("agricultural_probability")),
                        "ag_class": agg.get("ag_class", p.get("ag_class")),
                        "area_ha_est": p.get("area_ha_est"),
                        "water_stress_score": round(float(w), 2) if w is not None else None,
                        "vigor_stress_score": round(float(v), 2) if v is not None else None,
                        "alert": alert,
                        "possible_biotic_stress": biotic,
                        "biotic_status": agg.get("biotic_status") or p.get("biotic_status"),
                        "data_quality_confidence": round(dq, 1),
                        "source": clear_ok[0].get("source"),
                        "product_id": clear_ok[0].get("product_id"),
                        "tile": clear_ok[0].get("tile"),
                        "cloud_cover": clear_ok[0].get("cloud_cover"),
                        "series_scope": "aou_members_aggregate",
                        "persistence_status": p.get("persistence_status"),
                        "persistence_feature": agg.get("persistence_feature", p.get("persistence_feature")),
                        "n_dates_above_bare": agg.get("n_dates_above_bare", p.get("n_dates_above_bare")),
                        "refresh_status": refresh_status,
                        "observation_role": OBSERVATION_ROLE_CURRENT,
                        "assessability": "assessable",
                        "aggregate_id": agg.get("aggregate_id") or p.get("aggregate_id"),
                        "assessable_cell_fraction": agg.get("assessable_cell_fraction"),
                        "valid_area_fraction": agg.get("valid_area_fraction"),
                        # raw measures vs derived scores
                        "raw_measures": {"ndvi": round(float(ndvi), 4), "ndmi": round(float(ndmi), 4)},
                        "derived_scores": {
                            "water_stress_score": round(float(w), 2) if w is not None else None,
                            "vigor_stress_score": round(float(v), 2) if v is not None else None,
                            "agricultural_probability": agg.get("agricultural_probability", p.get("agricultural_probability")),
                            "ag_class": agg.get("ag_class", p.get("ag_class")),
                        },
                    }
                    if p.get("temporal_evidence_ar"):
                        row["temporal_evidence_ar"] = p["temporal_evidence_ar"]
                        row["temporal_evidence_en"] = p.get("temporal_evidence_en")
                        row["biotic_unknown_reason"] = p.get("biotic_unknown_reason")
                    by_date[str(obs_date)] = row

        obs = sorted(by_date.values(), key=lambda o: o.get("date") or "")
        n_clear = len(
            {
                str(o["date"])
                for o in obs
                if o.get("date")
                and o.get("series_scope") != "window_not_aou"
                and o.get("ndvi") is not None
            }
        )

        # Context only — never copied into observations[] / n_clear
        window_series = []
        for d in timeseries.get("dates", []):
            window_series.append(
                {
                    "date": d.get("date"),
                    "ndvi": (d.get("ndvi") or {}).get("mean"),
                    "ndmi": (d.get("ndmi") or {}).get("mean"),
                    "series_scope": "window_not_aou",
                    "note": "Window mean — AOI context only; not AOU ledger / n_clear",
                }
            )
        units.append(
            {
                "aou_id": aid,
                "n_clear_dates": n_clear,
                "observations": obs,
                "window_context_series": window_series,
                "honesty": (
                    "AOU ledger append/upserts by (aou_id, date); "
                    "window_context_series is context only (series_scope=window_not_aou)"
                ),
            }
        )

    return {
        "version": "0.4.6-evaluator-deep-recheck",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formula_ref": (
            "SCIENCE_LOCKS_v0.4_phase1_2.md + "
            "SCIENCE_LOCKS_v0.4_evaluator_endorsement.md + "
            "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
            "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
            "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md + "
            "SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md"
        ),
        "units": units,
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="v0.4 Phase-1 AgProb / AOU / stress enricher")
    parser.add_argument(
        "--alerts",
        type=Path,
        default=None,
        help="Input latest_alerts.geojson (default: MONITOR_OUT_DATA/latest_alerts.geojson)",
    )
    args = parser.parse_args()
    out = out_data_dir()
    alerts_path = args.alerts or (out / "latest_alerts.geojson")
    ts_path = out / "timeseries.json"
    aou_dir = out / "aou"
    aou_dir.mkdir(parents=True, exist_ok=True)
    registry_json = aou_dir / "aou_registry.json"
    registry_geojson = aou_dir / "aou_registry.geojson"
    observations_path = aou_dir / "aou_observations.json"

    if not alerts_path.exists():
        print(f"ERROR: missing {alerts_path}", file=sys.stderr)
        return 1

    geo = json.loads(alerts_path.read_text())
    ts = json.loads(ts_path.read_text()) if ts_path.exists() else {"dates": []}
    # Window / AOI timeseries length is CONTEXT ONLY — never AOU n_clear_dates.
    window_date_count = len(ts.get("dates") or [])
    date = geo.get("properties", {}).get("date") or (geo["features"][0]["properties"].get("date") if geo.get("features") else None)
    month = None
    if date:
        try:
            month = int(date.split("-")[1])
        except Exception:
            month = None

    ledger = _load_observations_ledger(observations_path)
    print(
        f"Enriching {len(geo.get('features', []))} cells; "
        f"AOU n_clear from ledger (append/upsert); "
        f"window_dates={window_date_count} (context only); date={date}"
    )
    enriched = enrich_features(geo["features"], month=month)
    enriched, registry, aou_feats, join_meta = assign_aou_ids(
        enriched,
        registry_json,
        date or "1970-01-01",
        ledger=ledger,
    )

    alert_counts = count_alerts(enriched)
    biotic_n = sum(1 for f in enriched if f["properties"].get("possible_biotic_stress"))
    import os as _os_rid
    run_id = (
        _os_rid.environ.get("MONITOR_RELEASE_ID")
        or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )

    props = dict(geo.get("properties") or {})
    props.update(
        {
            "source": props.get("source")
            or "Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer",
            "date": date,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "alert_counts": dict(alert_counts),
            "phase": "0.4.1-agriculture",
            "engines": [
                "agricultural_probability",
                "stress_scores",
                "biotic_risk",
                "aou_identity",
            ],
            "formula_ref": FORMULA_REF_POST,
            "ndre_note": "NDRE unavailable on offline enrich of existing grid; full STAC path reads B05/B06/B07",
            "geometry_kinds": ["monitoring_grid_500m", "aou_segment"],
            "aou_count": len(aou_feats),
            "possible_biotic_stress_count": biotic_n,
            "product_stamp": "provisional_satellite_analytical_service",
            "najd_model_validation": "not_validated",
            "evidence_level_default": "satellite_only",
            "window_date_count_context_only": window_date_count,
            "run_id": run_id,
            "join_rule": join_meta.get("join_rule", JOIN_RULE),
            "join_predicate": join_meta.get("join_predicate", "positive_area_overlap"),
            "consistency_status": "pending",
            "note": (
                "Alerts use Water/Vigor stress scores (expert v1) mapped to UI codes. "
                "AOU ≠ official farm. possible_biotic_stress ≠ pest certainty. "
                "Data-quality confidence ≠ ecological confidence. "
                "n_clear_dates from AOU observation ledger (append/upsert) — never window length. "
                "500m grid is fallback/debug; segmented AOUs are in aou/aou_registry.geojson. "
                "provisional_satellite_analytical_service; najd_model_validation=not_validated."
            ),
        }
    )
    geo_out = {
        "type": "FeatureCollection",
        "name": "najd_latest_alerts",
        "crs": geo.get("crs"),
        "properties": props,
        "features": enriched,
    }

    obs = build_observations(
        aou_feats,
        ts,
        enriched,
        existing_path=observations_path,
    )
    # Stamp shared aggregate_id with run_id so registry/ledger/decision match
    for feat in aou_feats:
        p = feat["properties"]
        agg = p.get("aou_date_aggregate")
        if isinstance(agg, dict):
            agg["run_id"] = run_id
            aid = p.get("aou_id")
            d = agg.get("date")
            agg["aggregate_id"] = f"{aid}|{d or 'none'}|{run_id}"
            p["aggregate_id"] = agg["aggregate_id"]
            p["aou_date_aggregate"] = agg
            # Mirror aggregate NDVI into consistency check fields
            if p.get("observation_role") == OBSERVATION_ROLE_CURRENT and agg.get("ndvi") is not None:
                # Ensure feature NDVI matches aggregate (single blob)
                p["ndvi"] = agg["ndvi"]
                p["ndmi"] = agg["ndmi"]
    for rec in registry.get("units") or []:
        agg = rec.get("aou_date_aggregate")
        if isinstance(agg, dict):
            agg["run_id"] = run_id
            agg["aggregate_id"] = f"{rec.get('aou_id')}|{agg.get('date') or 'none'}|{run_id}"
            rec["aggregate_id"] = agg["aggregate_id"]
            rec["aou_date_aggregate"] = agg
    # Re-copy aggregate fields onto observation rows for date T
    for unit in obs.get("units") or []:
        aid = unit.get("aou_id")
        feat_p = next((f["properties"] for f in aou_feats if f["properties"].get("aou_id") == aid), None)
        if not feat_p:
            continue
        agg = feat_p.get("aou_date_aggregate") or {}
        for row in unit.get("observations") or []:
            if row.get("date") == agg.get("date") and feat_p.get("observation_role") == OBSERVATION_ROLE_CURRENT:
                row["aggregate_id"] = agg.get("aggregate_id")
                row["ndvi"] = agg.get("ndvi", row.get("ndvi"))
                row["ndmi"] = agg.get("ndmi", row.get("ndmi"))
                row["persistence_feature"] = agg.get("persistence_feature", row.get("persistence_feature"))
                row["n_dates_above_bare"] = agg.get("n_dates_above_bare", row.get("n_dates_above_bare"))

    _sync_registry_from_ledger(registry, aou_feats, obs)
    registry["najd_model_validation"] = "not_validated"
    registry["formula_ref"] = (
        "SCIENCE_LOCKS_v0.4_phase1_2.md§2 + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
        "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
        "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md + "
        "SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md"
    )
    registry["active_means"] = "registry_identity_only"
    registry["join_rule"] = join_meta.get("join_rule", JOIN_RULE)

    reg_fc = {
        "type": "FeatureCollection",
        "name": "aou_registry",
        "properties": {
            "formula_ref": registry["formula_ref"],
            "aou_not_official_farm": True,
            "count": len(aou_feats),
            "product_stamp": "provisional_satellite_analytical_service",
            "najd_model_validation": "not_validated",
            "active_means": "registry_identity_only",
            "current_detection_enum": ["detected", "weak", "not_detected"],
            "join_rule": join_meta.get("join_rule", JOIN_RULE),
            "run_id": run_id,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
        "features": aou_feats,
    }

    # --- Unify timeseries alert_counts with enriched (single classifier) ---
    ts = ts if isinstance(ts, dict) else {"dates": []}
    ts["phase"] = "0.4.1-agriculture"
    ts["formula_ref"] = FORMULA_REF_POST
    ts["run_id"] = run_id
    method = ts.setdefault("method", {})
    indices = list(method.get("indices") or [])
    for item in [
        "NDRE=(B08-B05)/(B08+B05) [B06/B07 documented fallback only]",
        "AgProb=SCIENCE_LOCKS§1 expert_v1",
        "Stress=SCIENCE_LOCKS§3 expert_v1",
        "AlertUnify=map_stress_to_alert (same pass as latest_alerts)",
    ]:
        if item not in indices:
            indices.append(item)
    method["indices"] = indices
    method["aou_identity"] = (
        "AOU-NJ-######; join_rule=max_overlap_area; "
        "join_predicate=positive_area_overlap"
    )
    method["join_rule"] = join_meta.get("join_rule", JOIN_RULE)
    method["join_predicate"] = "positive_area_overlap"
    matched_date = False
    for entry in ts.get("dates") or []:
        if entry.get("date") == date:
            entry["alert_counts"] = dict(alert_counts)
            entry["grid_cell_count"] = len(enriched)
            entry["run_id"] = run_id
            entry["classifier"] = "map_stress_to_alert"
            matched_date = True
            break
    if date and not matched_date:
        (ts.setdefault("dates", [])).append(
            {
                "date": date,
                "alert_counts": dict(alert_counts),
                "grid_cell_count": len(enriched),
                "run_id": run_id,
                "classifier": "map_stress_to_alert",
            }
        )
    ts["last_updated"] = datetime.now(timezone.utc).isoformat()

    ts_counts = {}
    for entry in ts.get("dates") or []:
        if entry.get("date") == date:
            ts_counts = dict(entry.get("alert_counts") or {})
            break
    if date and not alert_counts_match(alert_counts, ts_counts):
        print(
            f"ERROR: alert/timeseries count mismatch for date={date} "
            f"alerts={dict(alert_counts)} timeseries={ts_counts}",
            file=sys.stderr,
        )
        props["consistency_status"] = "mismatch"
        # Keep last good published set — do not write
        return 3
    props["consistency_status"] = "ok"
    geo_out["properties"] = props

    # --- Atomic publish: stage then swap (R3-3/R3-4) ---
    import os
    import shutil
    import tempfile

    # When monitor owns the partner release, skip nested decision (R3-4: one decision run).
    skip_decision = os.environ.get("SKIP_DECISION_SCAFFOLDS", "").strip() in ("1", "true", "yes")

    stage = Path(tempfile.mkdtemp(prefix=f"observatory_publish_{run_id}_", dir=str(out)))
    try:
        (stage / "aou").mkdir(parents=True, exist_ok=True)
        (stage / "meta").mkdir(parents=True, exist_ok=True)
        (stage / "decision").mkdir(parents=True, exist_ok=True)
        (stage / "latest_alerts.geojson").write_text(json.dumps(geo_out))
        (stage / "timeseries.json").write_text(json.dumps(ts, indent=2))
        (stage / "aou" / "aou_observations.json").write_text(json.dumps(obs, indent=2))
        (stage / "aou" / "aou_registry.geojson").write_text(json.dumps(reg_fc))
        save_registry(stage / "aou" / "aou_registry.json", registry)
        release_id = run_id
        refresh = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": "run_ag_probability" + ("" if skip_decision else "+run_decision_scaffolds"),
            "run_id": run_id,
            "release_id": release_id,
            "artifacts": [
                "latest_alerts.geojson",
                "timeseries.json",
                "aou/aou_registry.geojson",
                "aou/aou_registry.json",
                "aou/aou_observations.json",
                "decision/aou_suitability_components.json",
                "decision/aou_confidence.json",
                "decision/aou_evidence_gaps.json",
                "decision/action_ladder.stubs.json",
                "decision/run_meta.json",
            ],
            "phase": "0.4.9-post30-followup",
            "formula_ref": FORMULA_REF_POST,
            "join_rule": join_meta.get("join_rule", JOIN_RULE),
            "join_predicate": "positive_area_overlap",
            "consistency_status": "ok",
            "mountain_seeding_hold": True,
            "observation_date": date,
            "alert_counts": dict(alert_counts),
            "min_clear_pixels_cell": DEFAULT_MIN_CLEAR_PIXELS_CELL,
            "min_clear_fraction_cell": DEFAULT_MIN_CLEAR_FRACTION_CELL,
            "min_clear_fraction_aou": DEFAULT_MIN_CLEAR_FRACTION_AOU,
            "min_clear_members_aou": DEFAULT_MIN_CLEAR_MEMBERS_AOU,
            "min_valid_area_fraction_aou": DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
            "valid_area_fraction_basis": "clear_pixels_in_aou",
            "release_pointer_semantics": "releases/<id>+CURRENT",
            "coverage_gate": {
                "min_clear_pixels_cell": DEFAULT_MIN_CLEAR_PIXELS_CELL,
                "min_clear_fraction_cell": DEFAULT_MIN_CLEAR_FRACTION_CELL,
                "min_clear_fraction_aou": DEFAULT_MIN_CLEAR_FRACTION_AOU,
                "min_clear_members_aou": DEFAULT_MIN_CLEAR_MEMBERS_AOU,
                "min_valid_area_fraction_aou": DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
                "assessable_cell_fraction": "secondary_count",
                "valid_area_fraction": "clear_pixels_in_aou",
                "valid_area_fraction_basis": "clear_pixels_in_aou",
            },
            "promote_includes_decision": not skip_decision,
            "single_staged_decision": True,
        }
        (stage / "meta" / "last_refresh.json").write_text(json.dumps(refresh, indent=2))
        (stage / "meta" / "run_meta.json").write_text(json.dumps(refresh, indent=2))

        if not skip_decision:
            # Standalone AgProb path: one decision run on this stage (unified release_id)
            prev_out = os.environ.get("MONITOR_OUT_DATA")
            os.environ["MONITOR_OUT_DATA"] = str(stage)
            try:
                from run_decision_scaffolds import main as decision_main
                drc = decision_main()
            except Exception as e:
                print(f"ERROR: decision scaffolds failed: {e}", file=sys.stderr)
                return 5
            finally:
                if prev_out is None:
                    os.environ.pop("MONITOR_OUT_DATA", None)
                else:
                    os.environ["MONITOR_OUT_DATA"] = prev_out
            if drc != 0:
                print(f"ERROR: decision scaffolds exited {drc}", file=sys.stderr)
                return drc if drc else 5
            # Stamp decision run_meta with same release_id BEFORE promote
            dmeta = stage / "decision" / "run_meta.json"
            if dmeta.is_file():
                try:
                    doc = json.loads(dmeta.read_text())
                    doc["release_id"] = release_id
                    doc["run_id"] = release_id
                    dmeta.write_text(json.dumps(doc, indent=2))
                except Exception:
                    pass

        required = [
            "latest_alerts.geojson",
            "timeseries.json",
            "aou/aou_observations.json",
            "aou/aou_registry.geojson",
            "aou/aou_registry.json",
            "meta/last_refresh.json",
            "meta/run_meta.json",
        ]
        if not skip_decision:
            required.extend(
                [
                    "decision/aou_suitability_components.json",
                    "decision/aou_confidence.json",
                    "decision/aou_evidence_gaps.json",
                    "decision/run_meta.json",
                ]
            )
        missing = [r for r in required if not (stage / r).exists()]
        if missing:
            print(f"ERROR: release missing {missing} — abort promote", file=sys.stderr)
            return 6

        promote = list(required)
        if not skip_decision:
            # Include optional action ladder when present
            if (stage / "decision" / "action_ladder.stubs.json").exists():
                promote.append("decision/action_ladder.stubs.json")
        # R4-4: stamp identical release_id on ALL partner artifacts before promote
        def _stamp_file(path: Path) -> None:
            if not path.is_file():
                return
            try:
                doc = json.loads(path.read_text())
            except Exception:
                return
            stamp_release_id_on_doc(doc, release_id)
            path.write_text(json.dumps(doc, indent=2 if path.suffix == ".json" else None))

        for rel in promote:
            _stamp_file(stage / rel)
        # Also ensure registry geojson FeatureCollection properties
        reg_gj = stage / "aou" / "aou_registry.geojson"
        if reg_gj.is_file():
            try:
                doc = json.loads(reg_gj.read_text())
                stamp_release_id_on_doc(doc, release_id)
                for f in doc.get("features") or []:
                    if isinstance(f.get("properties"), dict):
                        f["properties"]["release_id"] = release_id
                        f["properties"]["run_id"] = release_id
                reg_gj.write_text(json.dumps(doc))
            except Exception:
                pass
        alerts_f = stage / "latest_alerts.geojson"
        if alerts_f.is_file():
            try:
                doc = json.loads(alerts_f.read_text())
                stamp_release_id_on_doc(doc, release_id)
                for f in doc.get("features") or []:
                    if isinstance(f.get("properties"), dict):
                        f["properties"]["release_id"] = release_id
                        f["properties"]["run_id"] = release_id
                alerts_f.write_text(json.dumps(doc))
            except Exception:
                pass

        id_failures = verify_release_ids_match(stage, release_id, promote)
        if id_failures:
            print(
                f"ERROR: release_id gate failed {id_failures} — abort promote (pointer unchanged)",
                file=sys.stderr,
            )
            return 8

        try:
            publish_release_with_pointer(
                stage_root=stage,
                public_root=out,
                release_id=release_id,
                relative_paths=promote,
            )
        except Exception as e:
            print(
                f"ERROR: release pointer publish failed — CURRENT unchanged: {e}",
                file=sys.stderr,
            )
            return 7
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    print(f"Wrote {alerts_path} ({len(enriched)} features) run_id={run_id}")
    print(f"Wrote {observations_path} ({len(obs['units'])} units)")
    print(f"Wrote {registry_geojson} ({len(aou_feats)} AOUs)")
    print(f"Updated {ts_path} (alert_counts unified for {date})")
    print("Done.")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
