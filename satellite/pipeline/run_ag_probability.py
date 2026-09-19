#!/usr/bin/env python3
"""v0.4 Phase-1 Agricultural Probability + AOU identity + stress + biotic.

Modes:
  1) Offline enrich (default): read existing latest_alerts.geojson + timeseries.json,
     apply SCIENCE_LOCKS formulas, segment AOUs, write aou_registry / observations,
     and rewrite latest_alerts with new fields (ndre null if unavailable).
  2) Called after run_monitor.py full STAC path (same writers).

Cite: docs/SCIENCE_LOCKS_v0.4_phase1_2.md + SCIENCE_LOCKS_v0.4_evaluator_endorsement.md + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md
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
from engines.biotic import infer_biotic_from_cell  # noqa: E402
from engines.stress import (  # noqa: E402
    map_stress_to_alert,
    vigor_stress_score,
    water_stress_score,
)

BARE_NDVI = 0.18
EXPECTED_PIXELS = 2500


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
        prob = rec.get("agricultural_probability")
        if prob is not None:
            rec["ag_class"] = ag_class_from_probability(
                float(prob),
                n_clear_dates=n_clear,
                persistence_feature=0.0 if n_clear < 2 else 0.5,
                single_date_only=n_clear < 2,
            )
        rec["persistence_status"] = persistence_status(n_clear)

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
        prob = p.get("agricultural_probability")
        if prob is not None:
            p["ag_class"] = ag_class_from_probability(
                float(prob),
                n_clear_dates=n_clear,
                persistence_feature=0.0 if n_clear < 2 else 0.5,
                single_date_only=n_clear < 2,
            )
        p["persistence_status"] = persistence_status(n_clear)


def assign_aou_ids(
    features: list[dict],
    registry_json_path: Path,
    observation_date: str,
    ledger: dict[str, Any] | None = None,
) -> tuple[list[dict], dict[str, Any], list[dict]]:
    """Persistent AOUs: re-score existing units honestly; segment only if registry empty.

    n_clear from AOU observation ledger (distinct dates, series_scope != window_not_aou).
    FORBIDDEN: hardcoded n_clear_dates=1/4 forever; first_seen/last_seen alone; window length.
    Soft window persistence never raises class. active = registry identity only.
    """
    from engines.ag_probability import (
        ag_class_from_probability,
        agricultural_probability,
        persistence_status,
    )

    registry = load_registry(registry_json_path)
    aou_features: list[dict] = []
    cell_to_aou: dict[int, str] = {}
    active = [u for u in (registry.get("units") or []) if u.get("active", True) and u.get("geometry")]

    def _honest_class(prob: float | None, n_clear: int) -> str | None:
        if prob is None:
            return None
        return ag_class_from_probability(
            float(prob),
            n_clear_dates=n_clear,
            persistence_feature=0.0 if n_clear < 2 else 0.5,
            single_date_only=n_clear < 2,
        )

    def _score_unit_from_ndvi_ndmi(ndvi, ndmi, month: int | None, n_clear: int) -> dict:
        if ndvi is None or ndmi is None:
            return {"agricultural_probability": None, "ag_class": None}
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
        # Re-score path: keep N identities; do not mint from inflated window gates
        for rec in active:
            aou_id = rec["aou_id"]
            try:
                geom = shape(rec["geometry"])
            except Exception:
                continue

            intersecting: list[dict] = []
            vegetated: list[dict] = []
            for i, f in enumerate(features):
                try:
                    g = shape(f["geometry"])
                    if not geom.intersects(g):
                        continue
                    props = f["properties"]
                    intersecting.append(props)
                    cell_to_aou[i] = aou_id
                    if (props.get("ndvi") or 0) >= BARE_NDVI:
                        vegetated.append(props)
                except Exception:
                    continue

            # Append pending only when this run has polygon-covering clear NDVI
            cover_props = vegetated or intersecting
            pending_ndvi = None
            if cover_props:
                ndvi_vals = [m["ndvi"] for m in cover_props if m.get("ndvi") is not None]
                if ndvi_vals:
                    pending_ndvi = sum(ndvi_vals) / len(ndvi_vals)

            n_clear = _aou_scoped_clear_count(
                ledger,
                aou_id,
                pending_date=observation_date if pending_ndvi is not None else None,
                pending_ndvi=pending_ndvi,
            )

            scored = _score_unit_from_ndvi_ndmi(rec.get("ndvi"), rec.get("ndmi"), month, n_clear)
            mean_prob = scored["agricultural_probability"]
            if mean_prob is None:
                mean_prob = rec.get("agricultural_probability")
            ag_class = scored["ag_class"] or _honest_class(mean_prob, n_clear)
            pers_status = scored.get("persistence_status") or persistence_status(n_clear)

            detection = _current_detection_for_run(
                intersecting=intersecting,
                vegetated=vegetated,
                ag_class=ag_class,
            )
            member_count = len(vegetated) or len(intersecting) or rec.get("member_count")

            rec["agricultural_probability"] = mean_prob
            rec["ag_class"] = ag_class
            rec["n_clear_dates"] = n_clear
            rec["persistence_status"] = pers_status
            rec["current_detection"] = detection
            # active stays registry identity — do not retire on a miss
            rec["active"] = True if rec.get("active", True) else False

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
                        "agricultural_probability": mean_prob,
                        "ag_class": ag_class,
                        "area_ha_est": rec.get("area_ha_est"),
                        "ndvi": rec.get("ndvi"),
                        "ndmi": rec.get("ndmi"),
                        "ndre": None,
                        "ndre_available": False,
                        "ndre_status": "unavailable",
                        "member_count": member_count,
                        "geometry_kind": "aou_segment",
                        "aou_not_official_farm": True,
                        "n_clear_dates": n_clear,
                        "persistence_status": pers_status,
                        "persistence_estimated_from_window": False,
                        "evidence_level": "satellite_only",
                        "product_stamp": "provisional_satellite_analytical_service",
                        "najd_model_validation": "not_validated",
                        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§1-2 + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md",
                        "date": observation_date,
                    },
                }
            )
    else:
        # Cold start only: segment mask (honest cell scores; no window persistence gate)
        candidates = segment_probability_mask(features)
        for cand in candidates:
            n_clear = _aou_scoped_clear_count(
                ledger,
                aou_id="__cold_start__",
                pending_date=observation_date,
                pending_ndvi=cand.get("ndvi_mean"),
            )
            props = {
                "agricultural_probability": cand["agricultural_probability"],
                "ag_class": _honest_class(cand["agricultural_probability"], n_clear),
                "area_ha_est": cand["area_ha_est"],
                "n_clear_dates": n_clear,
                "persistence_status": persistence_status(n_clear),
            }
            aou_id, rec = mint_or_match_aou(
                cand["geometry"],
                registry,
                observation_date=observation_date,
                props=props,
            )
            for i, f in enumerate(features):
                try:
                    g = shape(f["geometry"])
                    if cand["geometry"].intersects(g):
                        cell_to_aou[i] = aou_id
                except Exception:
                    continue
            detection = "detected" if (cand.get("ndvi_mean") or 0) >= BARE_NDVI else "weak"
            rec["current_detection"] = detection
            rec["n_clear_dates"] = n_clear
            rec["active"] = True
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
                        "agricultural_probability": cand["agricultural_probability"],
                        "ag_class": props["ag_class"],
                        "area_ha_est": cand["area_ha_est"],
                        "ndvi": cand.get("ndvi_mean"),
                        "ndmi": cand.get("ndmi_mean"),
                        "ndre": None,
                        "ndre_available": False,
                        "ndre_status": "unavailable",
                        "member_count": cand["member_count"],
                        "geometry_kind": "aou_segment",
                        "aou_not_official_farm": True,
                        "n_clear_dates": n_clear,
                        "persistence_status": persistence_status(n_clear),
                        "persistence_estimated_from_window": False,
                        "evidence_level": "satellite_only",
                        "product_stamp": "provisional_satellite_analytical_service",
                        "najd_model_validation": "not_validated",
                        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§1-2 + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md",
                        "date": observation_date,
                    },
                }
            )

    for i, f in enumerate(features):
        if i in cell_to_aou:
            f["properties"]["aou_id"] = cell_to_aou[i]
        else:
            f["properties"].setdefault("aou_id", None)

    return features, registry, aou_features



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

        # Upsert today's AOU-scoped aggregate when members cover the polygon
        if members:
            ndvi_vals = [m["ndvi"] for m in members if m.get("ndvi") is not None]
            ndmi_vals = [m["ndmi"] for m in members if m.get("ndmi") is not None]
            if ndvi_vals:
                ndvi = sum(ndvi_vals) / len(ndvi_vals)
                ndmi = (sum(ndmi_vals) / len(ndmi_vals)) if ndmi_vals else None
                w = sum(m.get("water_stress_score") or 0 for m in members) / max(1, len(members))
                v = sum(m.get("vigor_stress_score") or 0 for m in members) / max(1, len(members))
                dq = sum(m.get("data_quality_confidence") or 0 for m in members) / max(1, len(members))
                biotic = any(m.get("possible_biotic_stress") for m in members)
                alerts = [m.get("alert") for m in members]
                alert = max(set(alerts), key=alerts.count) if alerts else "unclear"
                obs_date = p.get("date") or members[0].get("date")
                if obs_date:
                    by_date[str(obs_date)] = {
                        "aou_id": aid,
                        "date": str(obs_date),
                        "ndvi": round(ndvi, 4),
                        "ndmi": None if ndmi is None else round(ndmi, 4),
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
                    }

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
            "SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md"
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
    enriched, registry, aou_feats = assign_aou_ids(
        enriched,
        registry_json,
        date or "1970-01-01",
        ledger=ledger,
    )

    alert_counts: dict[str, int] = defaultdict(int)
    biotic_n = 0
    for f in enriched:
        alert_counts[f["properties"].get("alert", "unclear")] += 1
        if f["properties"].get("possible_biotic_stress"):
            biotic_n += 1

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
            "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md",
            "ndre_note": "NDRE unavailable on offline enrich of existing grid; full STAC path reads B05/B06/B07",
            "geometry_kinds": ["monitoring_grid_500m", "aou_segment"],
            "aou_count": len(aou_feats),
            "possible_biotic_stress_count": biotic_n,
            "product_stamp": "provisional_satellite_analytical_service",
            "najd_model_validation": "not_validated",
            "evidence_level_default": "satellite_only",
            "window_date_count_context_only": window_date_count,
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
    alerts_path.write_text(json.dumps(geo_out))
    print(f"Wrote {alerts_path} ({len(enriched)} features)")

    obs = build_observations(
        aou_feats,
        ts,
        enriched,
        existing_path=observations_path,
    )
    _sync_registry_from_ledger(registry, aou_feats, obs)
    registry["najd_model_validation"] = "not_validated"
    registry["formula_ref"] = (
        "SCIENCE_LOCKS_v0.4_phase1_2.md§2 + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md"
    )
    registry["active_means"] = "registry_identity_only"
    observations_path.write_text(json.dumps(obs, indent=2))
    print(f"Wrote {observations_path} ({len(obs['units'])} units)")

    save_registry(registry_json, registry)

    reg_fc = {
        "type": "FeatureCollection",
        "name": "aou_registry",
        "properties": {
            "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§2 + SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md",
            "aou_not_official_farm": True,
            "count": len(aou_feats),
            "product_stamp": "provisional_satellite_analytical_service",
            "najd_model_validation": "not_validated",
            "active_means": "registry_identity_only",
            "current_detection_enum": ["detected", "weak", "not_detected"],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
        "features": aou_feats,
    }
    registry_geojson.write_text(json.dumps(reg_fc))
    print(f"Wrote {registry_geojson} ({len(aou_feats)} AOUs)")

    # Update timeseries method block
    if ts_path.exists():
        ts["phase"] = "0.4.1-agriculture"
        ts["formula_ref"] = "SCIENCE_LOCKS_v0.4_phase1_2.md"
        method = ts.setdefault("method", {})
        indices = list(method.get("indices") or [])
        for item in [
            "NDRE=(B08-B05)/(B08+B05) [B06/B07 documented fallback only]",
            "AgProb=SCIENCE_LOCKS§1 expert_v1",
            "Stress=SCIENCE_LOCKS§3 expert_v1",
        ]:
            if item not in indices:
                indices.append(item)
        method["indices"] = indices
        method["aou_identity"] = "AOU-NJ-###### centroid+IoU>=0.3"
        ts["last_updated"] = datetime.now(timezone.utc).isoformat()
        ts_path.write_text(json.dumps(ts, indent=2))
        print(f"Updated {ts_path}")

    meta_dir = out / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    refresh = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": "run_ag_probability",
        "artifacts": [
            "latest_alerts.geojson",
            "timeseries.json",
            "aou/aou_registry.geojson",
            "aou/aou_registry.json",
            "aou/aou_observations.json",
        ],
        "phase": "0.4.1-agriculture",
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md",
    }
    (meta_dir / "last_refresh.json").write_text(json.dumps(refresh, indent=2))
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
