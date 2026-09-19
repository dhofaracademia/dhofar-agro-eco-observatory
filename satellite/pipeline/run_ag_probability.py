#!/usr/bin/env python3
"""v0.4 Phase-1 Agricultural Probability + AOU identity + stress + biotic.

Modes:
  1) Offline enrich (default): read existing latest_alerts.geojson + timeseries.json,
     apply SCIENCE_LOCKS formulas, segment AOUs, write aou_registry / observations,
     and rewrite latest_alerts with new fields (ndre null if unavailable).
  2) Called after run_monitor.py full STAC path (same writers).

Cite: docs/SCIENCE_LOCKS_v0.4_phase1_2.md + SCIENCE_LOCKS_v0.4_evaluator_endorsement.md + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + SCIENCE_LOCKS_v0.4_observation_integrity.md + SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md
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
    segment_probability_mask,
)
from engines.observation_integrity import (  # noqa: E402
    DEFAULT_MIN_CLEAR_FRACTION_AOU,
    DEFAULT_MIN_CLEAR_FRACTION_CELL,
    DEFAULT_MIN_CLEAR_MEMBERS_AOU,
    DEFAULT_MIN_CLEAR_PIXELS_CELL,
    JOIN_RULE,
    alert_counts_match,
    aou_assessability,
    assign_cells_max_overlap,
    cell_assessability,
    count_alerts,
    ledger_persistence_feature,
    ledger_sequence_rows,
    ledger_stress_flags,
    member_clear_means,
    positive_area_overlap,
    temporal_evidence_labels,
)
from engines.biotic import infer_biotic_from_cell  # noqa: E402
from engines.stress import (  # noqa: E402
    map_stress_to_alert,
    vigor_stress_score,
    water_stress_score,
)

BARE_NDVI = 0.18
EXPECTED_PIXELS = 2500

# Published formula_ref (lock §B / post-integrity evaluator)
FORMULA_REF_POST = (
    "SCIENCE_LOCKS_v0.4_phase1_2.md + "
    "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
    "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
    "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md"
)
FORMULA_REF_AOU = (
    "SCIENCE_LOCKS_v0.4_phase1_2.md§1-2 + "
    "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
    "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
    "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md"
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


def cell_key(props: dict) -> str:
    # Stable debug key only — NOT AOU identity (SCIENCE_LOCKS §2.2)
    return f"grid:{props.get('date')}:{round(props.get('ndvi', 0), 4)}:{round(props.get('ndmi', 0), 4)}:{props.get('pixel_count')}"


def enrich_features(features: list[dict], *, month: int | None) -> list[dict]:
    """Apply AgProb + stress + biotic to monitoring-grid features.

    n_clear_dates is per-cell / AOU-scoped SCL-clear count — NEVER the
    AOI timeseries window length (SCIENCE_LOCKS evaluator endorsement).
    Offline enrich has one observation date per cell → n_clear_dates=1.
    Stress calls use stress_flags_recent=[] here (renorm/null). After AOU
    assign, multi-date units (n_clear≥2) re-score via ledger flags.
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
        if not biotic["possible_biotic_stress"] and not te["temporal_evidence_sufficient"]:
            p["biotic_status"] = "unknown_insufficient_temporal_evidence"
            p["biotic_unknown_reason"] = "insufficient_temporal_evidence"
        # Per-cell clear-coverage gate (scene clear ≠ cell assessable)
        p["assessability"] = cell_assessability(
            p,
            min_clear_pixels=DEFAULT_MIN_CLEAR_PIXELS_CELL,
            min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_CELL,
        )
        if p["assessability"] == "unassessable":
            # Do not invent stress/ag scores as observed — keep indices, stamp honesty
            p["alert"] = "unclear"
            p["ag_class"] = "unassessable"

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
) -> int:
    """Distinct ledger dates where series_scope != window_not_aou.

    Forbidden sources: first_seen/last_seen alone; hardcoded 1/4; window length.
    Optional pending_* includes today's clear row about to be upserted.
    """
    dates = _ledger_dates_for_aou(ledger, aou_id)
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
) -> tuple[float | None, int, int, str]:
    """Ledger-sequence persistence only — never invent 0.5 from n_clear>=2 alone."""
    unit = _unit_from_ledger(ledger, aou_id)
    rows = ledger_sequence_rows(unit)
    if pending_date and pending_ndvi is not None:
        # Include pending clear observation in sequence for this run
        if not any(str(r.get("date")) == str(pending_date) for r in rows):
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
    n_clear_dates: int,
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
) -> list[bool]:
    """Empty flags mean renorm — never 'no stress / healthy'."""
    return ledger_stress_flags(ledger_sequence_rows(_unit_from_ledger(ledger, aou_id)), kind=kind)

def _current_detection_for_run(
    *,
    intersecting: list[dict],
    vegetated: list[dict],
    ag_class: str | None,
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
    obs_doc: dict[str, Any],
) -> None:
    """n_clear + first_seen/last_seen from ledger; re-gate ag_class/persistence."""
    from engines.ag_probability import ag_class_from_probability, persistence_status

    by_id = {u["aou_id"]: u for u in obs_doc.get("units") or []}
    for rec in registry.get("units") or []:
        aid = rec.get("aou_id")
        unit = by_id.get(aid) or {}
        dates = sorted(_ledger_dates_for_aou({"units": [unit]}, aid))
        n_clear = len(dates)
        rec["n_clear_dates"] = n_clear
        if dates:
            rec["first_seen_date"] = dates[0]
            rec["last_seen_date"] = dates[-1]
        rows = ledger_sequence_rows(unit)
        pers_feat, n_seq, n_above = ledger_persistence_feature(rows, bare_ndvi=BARE_NDVI)
        rec["n_dates_above_bare"] = n_above
        rec["persistence_feature"] = pers_feat  # None when sequence insufficient
        prob = rec.get("agricultural_probability")
        if prob is not None:
            rec["ag_class"] = ag_class_from_probability(
                float(prob),
                n_clear_dates=n_clear,
                persistence_feature=0.0 if pers_feat is None else float(pers_feat),
                single_date_only=n_clear < 2,
            )
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
            p["last_seen_date"] = dates[-1]
        if unit.get("n_clear_dates") is not None:
            p["n_clear_dates"] = int(unit["n_clear_dates"])
            n_clear = int(unit["n_clear_dates"])
        rows = ledger_sequence_rows(unit)
        pers_feat, n_seq, n_above = ledger_persistence_feature(rows, bare_ndvi=BARE_NDVI)
        p["n_dates_above_bare"] = n_above
        p["persistence_feature"] = pers_feat
        prob = p.get("agricultural_probability")
        if prob is not None:
            p["ag_class"] = ag_class_from_probability(
                float(prob),
                n_clear_dates=n_clear,
                persistence_feature=0.0 if pers_feat is None else float(pers_feat),
                single_date_only=n_clear < 2,
            )
        p["persistence_status"] = persistence_status(n_clear) if (n_clear < 2 or pers_feat is not None) else "insufficient_sequence"


def assign_aou_ids(
    features: list[dict],
    registry_json_path: Path,
    observation_date: str,
    ledger: dict[str, Any] | None = None,
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

    def _score_unit_from_ndvi_ndmi(ndvi, ndmi, month: int | None, n_clear: int) -> dict:
        if ndvi is None or ndmi is None:
            return {"agricultural_probability": None, "ag_class": None, "persistence_status": persistence_status(n_clear)}
        ag = agricultural_probability(
            ndvi=float(ndvi),
            ndmi=float(ndmi),
            n_clear_dates=n_clear,
            n_dates_above_bare=1 if float(ndvi) >= BARE_NDVI else 0,
            month=month,
        )
        return {
            "agricultural_probability": ag["agricultural_probability"],
            "ag_class": ag["ag_class"],
            "persistence_status": ag.get("persistence_status", persistence_status(n_clear)),
        }

    month = None
    if observation_date:
        try:
            month = int(str(observation_date).split("-")[1])
        except Exception:
            month = None

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
            # Per-cell assessability before AOU aggregate
            for m in members:
                m["assessability"] = cell_assessability(
                    m,
                    min_clear_pixels=DEFAULT_MIN_CLEAR_PIXELS_CELL,
                    min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_CELL,
                )
            assess, assess_meta = aou_assessability(
                members,
                min_clear_fraction=DEFAULT_MIN_CLEAR_FRACTION_AOU,
                min_clear_members=DEFAULT_MIN_CLEAR_MEMBERS_AOU,
            )
            clear_members = [m for m in members if m.get("assessability") == "assessable"]
            mean_ndvi, mean_ndmi = member_clear_means(clear_members)

            has_new = assess == "assessable" and mean_ndvi is not None and mean_ndmi is not None
            pending_ndvi = mean_ndvi if has_new else None
            n_clear = _aou_scoped_clear_count(
                ledger,
                aou_id,
                pending_date=observation_date if has_new else None,
                pending_ndvi=pending_ndvi,
            )
            pers_feat, _ns, n_above, pers_stat = _persistence_feature_from_ledger(
                ledger,
                aou_id,
                pending_ndvi=pending_ndvi,
                pending_date=observation_date if has_new else None,
            )
            water_flags = _stress_flags_from_ledger(ledger, aou_id, kind="water")
            vigor_flags = _stress_flags_from_ledger(ledger, aou_id, kind="vigor")
            # A: when n_clear≥2, feed ledger flags into member stress scores
            # (enrich_features still passes [] at n_clear=1 — renorm/null OK)
            if n_clear >= 2 and members:
                for m in members:
                    _rescore_stress_with_ledger_flags(
                        m,
                        water_flags=water_flags,
                        vigor_flags=vigor_flags,
                        month=month,
                        n_clear_dates=n_clear,
                    )
            te = temporal_evidence_labels(n_clear)

            if not members:
                # No positive-area members this run — keep prior dated scores; do not advance
                refresh_status = "no_new_observation"
                mean_prob = rec.get("agricultural_probability")
                ag_class = _honest_class(mean_prob, n_clear, pers_feat) or rec.get("ag_class")
                pers_status = pers_stat or persistence_status(n_clear)
                stamp_date = rec.get("last_seen_date")
                out_ndvi, out_ndmi = rec.get("ndvi"), rec.get("ndmi")
            elif assess == "unassessable":
                # Members present but clear-coverage below gate — unassessable, no date advance
                refresh_status = "unassessable_coverage"
                mean_prob = rec.get("agricultural_probability")
                ag_class = "unassessable"
                pers_status = pers_stat or persistence_status(n_clear)
                stamp_date = rec.get("last_seen_date")
                out_ndvi, out_ndmi = rec.get("ndvi"), rec.get("ndmi")
            elif has_new:
                scored = _score_unit_from_ndvi_ndmi(mean_ndvi, mean_ndmi, month, n_clear)
                mean_prob = scored["agricultural_probability"]
                ag_class = scored["ag_class"] or _honest_class(mean_prob, n_clear, pers_feat)
                pers_status = pers_stat or scored.get("persistence_status") or persistence_status(n_clear)
                refresh_status = "refreshed"
                stamp_date = observation_date
                rec["ndvi"] = round(mean_ndvi, 4)
                rec["ndmi"] = round(mean_ndmi, 4)
                rec["last_seen_date"] = observation_date
                out_ndvi, out_ndmi = rec["ndvi"], rec["ndmi"]
            else:
                # No valid new clear in-boundary sample — keep prior dated scores; do not advance date
                refresh_status = "stale" if (rec.get("ndvi") is None or rec.get("ndmi") is None or not members) else "no_new_observation"
                if not members:
                    refresh_status = "no_new_observation"
                mean_prob = rec.get("agricultural_probability")
                ag_class = _honest_class(mean_prob, n_clear, pers_feat) or rec.get("ag_class")
                pers_status = pers_stat or persistence_status(n_clear)
                stamp_date = rec.get("last_seen_date")  # prior date only
                out_ndvi, out_ndmi = rec.get("ndvi"), rec.get("ndmi")

            detection = _current_detection_for_run(
                intersecting=members,
                vegetated=vegetated,
                ag_class=ag_class,
            )
            member_count = len(vegetated) or len(members) or rec.get("member_count")

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
                        "stress_flags_recent_water": water_flags,
                        "stress_flags_recent_vigor": vigor_flags,
                        "water_stress_score": (
                            round(
                                sum(m.get("water_stress_score") or 0 for m in (clear_members or members))
                                / max(1, len(clear_members or members)),
                                2,
                            )
                            if (clear_members or members)
                            else None
                        ),
                        "vigor_stress_score": (
                            round(
                                sum(m.get("vigor_stress_score") or 0 for m in (clear_members or members))
                                / max(1, len(clear_members or members)),
                                2,
                            )
                            if (clear_members or members)
                            else None
                        ),
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
    else:
        # Cold start only
        candidates = segment_probability_mask(features)
        # Clear then assign via positive-area max overlap against candidate polys
        cand_geoms = []
        for idx, cand in enumerate(candidates):
            cand_geoms.append((f"__cand_{idx}", cand["geometry"]))
        by_cand = assign_cells_max_overlap(features, cand_geoms, bare_ndvi=BARE_NDVI)

        for idx, cand in enumerate(candidates):
            cand_key = f"__cand_{idx}"
            mean_ndvi = cand.get("ndvi_mean")
            mean_ndmi = cand.get("ndmi_mean")
            # Prefer means from positive-area members
            m_ndvi, m_ndmi = member_clear_means((by_cand.get(cand_key) or {}).get("members") or [])
            if m_ndvi is not None:
                mean_ndvi, mean_ndmi = m_ndvi, m_ndmi
            has_new = mean_ndvi is not None and mean_ndmi is not None
            n_clear = _aou_scoped_clear_count(
                ledger,
                aou_id="__cold_start__",
                pending_date=observation_date if has_new else None,
                pending_ndvi=mean_ndvi if has_new else None,
            )
            te = temporal_evidence_labels(n_clear)
            scored = _score_unit_from_ndvi_ndmi(mean_ndvi, mean_ndmi, month, n_clear) if has_new else {
                "agricultural_probability": cand.get("agricultural_probability"),
                "ag_class": _honest_class(cand.get("agricultural_probability"), n_clear),
                "persistence_status": persistence_status(n_clear),
            }
            props = {
                "agricultural_probability": scored["agricultural_probability"],
                "ag_class": scored["ag_class"] or _honest_class(scored["agricultural_probability"], n_clear),
                "area_ha_est": cand["area_ha_est"],
                "n_clear_dates": n_clear,
                "persistence_status": scored.get("persistence_status") or persistence_status(n_clear),
            }
            aou_id, rec = mint_or_match_aou(
                cand["geometry"],
                registry,
                observation_date=observation_date if has_new else (observation_date or "1970-01-01"),
                props=props,
            )
            # Re-stamp cell aou_ids from candidate key → real id
            for i in (by_cand.get(cand_key) or {}).get("member_indices") or []:
                features[i]["properties"]["aou_id"] = aou_id
            if has_new:
                rec["ndvi"] = round(float(mean_ndvi), 4)
                rec["ndmi"] = round(float(mean_ndmi), 4)
                refresh_status = "refreshed"
                stamp_date = observation_date
            else:
                refresh_status = "no_new_observation"
                stamp_date = rec.get("last_seen_date")
            detection = "detected" if (mean_ndvi or 0) >= BARE_NDVI else "weak"
            rec["current_detection"] = detection
            rec["n_clear_dates"] = n_clear
            rec["refresh_status"] = refresh_status
            rec["active"] = True
            for k, v in te.items():
                rec[k] = v
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
                        "current_detection": detection,
                        "refresh_status": refresh_status,
                        "agricultural_probability": props["agricultural_probability"],
                        "ag_class": props["ag_class"],
                        "area_ha_est": cand["area_ha_est"],
                        "ndvi": rec.get("ndvi"),
                        "ndmi": rec.get("ndmi"),
                        "ndre": None,
                        "ndre_available": False,
                        "ndre_status": "unavailable",
                        "member_count": cand["member_count"],
                        "geometry_kind": "aou_segment",
                        "aou_not_official_farm": True,
                        "n_clear_dates": n_clear,
                        "persistence_status": props["persistence_status"],
                        "persistence_estimated_from_window": False,
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

    # Ensure every cell has explicit aou_id (None if unassigned)
    for f in features:
        f["properties"].setdefault("aou_id", None)

    return features, registry, aou_features, join_meta



def build_observations(
    aou_features: list[dict],
    timeseries: dict[str, Any],
    enriched_cells: list[dict],
    existing_path: Path | None = None,
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

        # Upsert only when this run refreshed with valid clear member NDVI+NDMI.
        # Stale / no_new_observation → keep prior ledger rows; do NOT stamp new date.
        refresh_status = p.get("refresh_status") or "refreshed"
        if members and refresh_status == "refreshed":
            ndvi_vals = [m["ndvi"] for m in members if m.get("ndvi") is not None]
            ndmi_vals = [m["ndmi"] for m in members if m.get("ndmi") is not None]
            pairs_ok = [
                m for m in members
                if m.get("ndvi") is not None and m.get("ndmi") is not None
            ]
            if pairs_ok:
                ndvi = sum(m["ndvi"] for m in pairs_ok) / len(pairs_ok)
                ndmi = sum(m["ndmi"] for m in pairs_ok) / len(pairs_ok)
                w = sum(m.get("water_stress_score") or 0 for m in members) / max(1, len(members))
                v = sum(m.get("vigor_stress_score") or 0 for m in members) / max(1, len(members))
                dq = sum(m.get("data_quality_confidence") or 0 for m in members) / max(1, len(members))
                # Empty temporal history ≠ "no biotic" — only flag when rules fire;
                # stamp insufficient temporal evidence when n_clear < 2.
                biotic = any(m.get("possible_biotic_stress") for m in members)
                alerts = [m.get("alert") for m in members]
                alert = max(set(alerts), key=alerts.count) if alerts else "unclear"
                obs_date = p.get("date") or members[0].get("date")
                if obs_date:
                    row = {
                        "aou_id": aid,
                        "date": str(obs_date),
                        "ndvi": round(ndvi, 4),
                        "ndmi": round(ndmi, 4),
                        "ndre": None,
                        "ndre_available": False,
                        "agricultural_probability": p.get("agricultural_probability"),
                        "ag_class": p.get("ag_class"),
                        "area_ha_est": p.get("area_ha_est"),
                        "water_stress_score": round(w, 2),
                        "vigor_stress_score": round(v, 2),
                        "alert": alert,
                        "possible_biotic_stress": biotic,
                        "data_quality_confidence": round(dq, 1),
                        "source": members[0].get("source"),
                        "product_id": members[0].get("product_id"),
                        "tile": members[0].get("tile"),
                        "cloud_cover": members[0].get("cloud_cover"),
                        "series_scope": "aou_members_aggregate",
                        "persistence_status": p.get("persistence_status"),
                        "refresh_status": refresh_status,
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
        "version": "0.4.5-aou-temporal-ledger",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formula_ref": (
            "SCIENCE_LOCKS_v0.4_phase1_2.md + "
            "SCIENCE_LOCKS_v0.4_evaluator_endorsement.md + "
            "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
            "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
            "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md"
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
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

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
    _sync_registry_from_ledger(registry, aou_feats, obs)
    registry["najd_model_validation"] = "not_validated"
    registry["formula_ref"] = (
        "SCIENCE_LOCKS_v0.4_phase1_2.md§2 + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md + "
        "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
        "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md"
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

    # --- Atomic publish: stage then swap ---
    import shutil
    import tempfile

    stage = Path(tempfile.mkdtemp(prefix=f"observatory_publish_{run_id}_", dir=str(out)))
    try:
        (stage / "aou").mkdir(parents=True, exist_ok=True)
        (stage / "meta").mkdir(parents=True, exist_ok=True)
        (stage / "latest_alerts.geojson").write_text(json.dumps(geo_out))
        (stage / "timeseries.json").write_text(json.dumps(ts, indent=2))
        (stage / "aou" / "aou_observations.json").write_text(json.dumps(obs, indent=2))
        (stage / "aou" / "aou_registry.geojson").write_text(json.dumps(reg_fc))
        # registry json via save_registry into stage
        save_registry(stage / "aou" / "aou_registry.json", registry)
        refresh = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": "run_ag_probability",
            "run_id": run_id,
            "artifacts": [
                "latest_alerts.geojson",
                "timeseries.json",
                "aou/aou_registry.geojson",
                "aou/aou_registry.json",
                "aou/aou_observations.json",
            ],
            "phase": "0.4.1-agriculture",
            "formula_ref": FORMULA_REF_POST,
            "join_rule": join_meta.get("join_rule", JOIN_RULE),
            "join_predicate": "positive_area_overlap",
            "consistency_status": "ok",
            "mountain_seeding_hold": True,
            "observation_date": date,
            "alert_counts": dict(alert_counts),
            # lock §1 — cell/AOU clear-coverage thresholds
            "min_clear_pixels_cell": DEFAULT_MIN_CLEAR_PIXELS_CELL,
            "min_clear_fraction_cell": DEFAULT_MIN_CLEAR_FRACTION_CELL,
            "min_clear_fraction_aou": DEFAULT_MIN_CLEAR_FRACTION_AOU,
            "min_clear_members_aou": DEFAULT_MIN_CLEAR_MEMBERS_AOU,
            "coverage_gate": {
                "min_clear_pixels_cell": DEFAULT_MIN_CLEAR_PIXELS_CELL,
                "min_clear_fraction_cell": DEFAULT_MIN_CLEAR_FRACTION_CELL,
                "min_clear_fraction_aou": DEFAULT_MIN_CLEAR_FRACTION_AOU,
                "min_clear_members_aou": DEFAULT_MIN_CLEAR_MEMBERS_AOU,
            },
        }
        (stage / "meta" / "last_refresh.json").write_text(json.dumps(refresh, indent=2))
        (stage / "meta" / "run_meta.json").write_text(json.dumps(refresh, indent=2))

        # Swap into place
        shutil.move(str(stage / "latest_alerts.geojson"), str(alerts_path))
        shutil.move(str(stage / "timeseries.json"), str(ts_path))
        aou_dir.mkdir(parents=True, exist_ok=True)
        for name in ("aou_observations.json", "aou_registry.geojson", "aou_registry.json"):
            shutil.move(str(stage / "aou" / name), str(aou_dir / name))
        meta_dir = out / "meta"
        meta_dir.mkdir(parents=True, exist_ok=True)
        for name in ("last_refresh.json", "run_meta.json"):
            shutil.move(str(stage / "meta" / name), str(meta_dir / name))
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
