#!/usr/bin/env python3
"""v0.4 Phase-1 Agricultural Probability + AOU identity + stress + biotic.

Modes:
  1) Offline enrich (default): read existing latest_alerts.geojson + timeseries.json,
     apply SCIENCE_LOCKS formulas, segment AOUs, write aou_registry / observations,
     and rewrite latest_alerts with new fields (ndre null if unavailable).
  2) Called after run_monitor.py full STAC path (same writers).

Cite: docs/SCIENCE_LOCKS_v0.4_phase1_2.md
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


def enrich_features(features: list[dict], *, n_clear_dates: int, month: int | None) -> list[dict]:
    """Apply AgProb + stress + biotic to monitoring-grid features."""
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

        # Without per-cell multi-date history, estimate persistence from window
        # clear-date count when the cell is currently vegetated (documented).
        if ndvi >= BARE_NDVI and n_clear_dates >= 2:
            n_above = min(n_clear_dates, 3)
            persistence_estimated = True
        else:
            n_above = 1 if ndvi >= BARE_NDVI else 0
            persistence_estimated = False
        persistence_gate = n_clear_dates >= 2 and ndvi >= BARE_NDVI

        ag = agricultural_probability(
            ndvi=ndvi,
            ndmi=ndmi,
            ndre=ndre if ndre_available else None,
            ndre_available=ndre_available,
            n_clear_dates=n_clear_dates,
            n_dates_above_bare=n_above,
            month=month,
            local_variance=None,
        )
        p["agricultural_probability"] = ag["agricultural_probability"]
        p["ag_class"] = ag["ag_class"]
        p["ag_probability_status"] = "expert_v1"
        p["persistence_gate"] = persistence_gate or ag["features"].get("persistence", 0) >= 0.5
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
        )
        vigor = vigor_stress_score(
            ndvi=ndvi,
            ndvi_p25_veg=p.get("ndvi_p25_veg", 0.25),
            ndvi_p50_veg=None,
            ndvi_hist_median=None,
            ndre=ndre if ndre_available else None,
            stress_flags_recent=[],
            month=month,
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


def assign_aou_ids(
    features: list[dict],
    registry_json_path: Path,
    observation_date: str,
) -> tuple[list[dict], dict[str, Any], list[dict]]:
    """Segment high-probability cells → persistent AOUs; stamp aou_id on members."""
    registry = load_registry(registry_json_path)
    candidates = segment_probability_mask(features)
    aou_features = []
    cell_to_aou: dict[int, str] = {}

    # Map member cells by identity of properties object id — use geometry wkt-ish
    for cand in candidates:
        props = {
            "agricultural_probability": cand["agricultural_probability"],
            "ag_class": None,
            "area_ha_est": cand["area_ha_est"],
        }
        # derive ag_class from mean probability
        from engines.ag_probability import ag_class_from_probability

        if cand["agricultural_probability"] is not None:
            props["ag_class"] = ag_class_from_probability(
                cand["agricultural_probability"],
                n_clear_dates=4,
                persistence_feature=0.5,
            )
        aou_id, rec = mint_or_match_aou(
            cand["geometry"],
            registry,
            observation_date=observation_date,
            props=props,
        )
        # mark member cells: match by centroid proximity of cell polygons
        for i, f in enumerate(features):
            try:
                g = shape(f["geometry"])
                if cand["geometry"].intersects(g):
                    cell_to_aou[i] = aou_id
            except Exception:
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
                    "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§1-2",
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
) -> dict[str, Any]:
    """Per-AOU series: prefer cell aggregates at latest date; stub window series honestly."""
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
        # Latest observation from members
        obs = []
        if members:
            ndvi = sum(m["ndvi"] for m in members if m.get("ndvi") is not None) / max(
                1, sum(1 for m in members if m.get("ndvi") is not None)
            )
            ndmi = sum(m["ndmi"] for m in members if m.get("ndmi") is not None) / max(
                1, sum(1 for m in members if m.get("ndmi") is not None)
            )
            w = sum(m.get("water_stress_score") or 0 for m in members) / max(1, len(members))
            v = sum(m.get("vigor_stress_score") or 0 for m in members) / max(1, len(members))
            dq = sum(m.get("data_quality_confidence") or 0 for m in members) / max(1, len(members))
            biotic = any(m.get("possible_biotic_stress") for m in members)
            alerts = [m.get("alert") for m in members]
            alert = max(set(alerts), key=alerts.count) if alerts else "unclear"
            obs.append(
                {
                    "aou_id": aid,
                    "date": p.get("date"),
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
                }
            )
        # Honest window-level companion points (not AOU-true history yet)
        window_series = []
        for d in timeseries.get("dates", []):
            window_series.append(
                {
                    "date": d.get("date"),
                    "ndvi": (d.get("ndvi") or {}).get("mean"),
                    "ndmi": (d.get("ndmi") or {}).get("mean"),
                    "series_scope": "window_not_aou",
                    "note": "Window mean — AOU-specific history not yet multi-date tracked",
                }
            )
        units.append(
            {
                "aou_id": aid,
                "observations": obs,
                "window_context_series": window_series,
                "honesty": "AOU multi-date history grows as monitor re-runs with registry matching",
            }
        )

    return {
        "version": "0.4.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md",
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
    n_clear = max(1, len(ts.get("dates") or []))
    date = geo.get("properties", {}).get("date") or (geo["features"][0]["properties"].get("date") if geo.get("features") else None)
    month = None
    if date:
        try:
            month = int(date.split("-")[1])
        except Exception:
            month = None

    print(f"Enriching {len(geo.get('features', []))} cells; n_clear_dates={n_clear} date={date}")
    enriched = enrich_features(geo["features"], n_clear_dates=n_clear, month=month)
    enriched, registry, aou_feats = assign_aou_ids(enriched, registry_json, date or "1970-01-01")

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
            "note": (
                "Alerts use Water/Vigor stress scores (expert v1) mapped to UI codes. "
                "AOU ≠ official farm. possible_biotic_stress ≠ pest certainty. "
                "Data-quality confidence ≠ ecological confidence. "
                "500m grid is fallback/debug; segmented AOUs are in aou/aou_registry.geojson."
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

    save_registry(registry_json, registry)

    reg_fc = {
        "type": "FeatureCollection",
        "name": "aou_registry",
        "properties": {
            "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§2",
            "aou_not_official_farm": True,
            "count": len(aou_feats),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
        "features": aou_feats,
    }
    registry_geojson.write_text(json.dumps(reg_fc))
    print(f"Wrote {registry_geojson} ({len(aou_feats)} AOUs)")

    obs = build_observations(aou_feats, ts, enriched)
    observations_path.write_text(json.dumps(obs, indent=2))
    print(f"Wrote {observations_path} ({len(obs['units'])} units)")

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
