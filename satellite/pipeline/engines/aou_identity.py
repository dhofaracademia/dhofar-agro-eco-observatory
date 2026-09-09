"""Persistent AOU identity — SCIENCE_LOCKS §2.

ID format: AOU-NJ-{NNNNNN}
Match: centroid proximity max(150m, 0.5*sqrt(area)) then IoU ≥ 0.3.
Never bind identity to 500 m cell index.
Min component area ~2 ha.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

MIN_AREA_HA = 2.0
IOU_THR = 0.3
REGION = "NJ"


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def centroid_xy(geom) -> tuple[float, float]:
    c = geom.centroid
    return float(c.x), float(c.y)


def match_radius_m(area_m2: float) -> float:
    return max(150.0, 0.5 * math.sqrt(max(area_m2, 0.0)))


def iou(a, b) -> float:
    inter = a.intersection(b).area
    union = a.union(b).area
    if union <= 0:
        return 0.0
    return float(inter / union)


def next_id(registry: dict[str, Any]) -> str:
    used = []
    for rec in registry.get("units", []):
        try:
            used.append(int(str(rec["aou_id"]).split("-")[-1]))
        except (ValueError, KeyError, IndexError):
            continue
    n = max(used) + 1 if used else 1
    return f"AOU-{REGION}-{n:06d}"


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "type": "aou_registry",
            "version": "0.4.1",
            "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§2",
            "units": [],
            "updated_at": None,
        }
    return json.loads(path.read_text())


def save_registry(path: Path, registry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(registry, indent=2))


def mint_or_match_aou(
    geom,
    registry: dict[str, Any],
    *,
    observation_date: str,
    props: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Match existing unit or mint new ID. Mutates registry['units']."""
    props = props or {}
    lon, lat = centroid_xy(geom)
    area_m2 = float(geom.area)  # degrees^2 if geographic — prefer props area
    area_ha = props.get("area_ha_est")
    if area_ha is not None:
        area_m2 = float(area_ha) * 10_000.0
    else:
        # rough deg^2 → m2 at ~18N
        mid_lat = lat
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(math.radians(mid_lat))
        area_m2 = abs(geom.area) * m_per_deg_lat * m_per_deg_lon
        area_ha = area_m2 / 10_000.0

    radius = match_radius_m(area_m2)
    candidates: list[tuple[float, dict]] = []
    for rec in registry.get("units", []):
        if not rec.get("active", True):
            continue
        clon = rec.get("centroid_lon")
        clat = rec.get("centroid_lat")
        if clon is None or clat is None:
            continue
        dist = _haversine_m(lon, lat, float(clon), float(clat))
        if dist > radius:
            continue
        prev_geom = None
        if rec.get("geometry"):
            prev_geom = shape(rec["geometry"])
            ov = iou(geom, prev_geom)
            if ov < IOU_THR:
                continue
            candidates.append((ov, rec))
        else:
            # centroid-only match if no stored geometry
            candidates.append((0.3 + (1.0 - dist / radius) * 0.1, rec))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_iou, rec = candidates[0]
        rec["centroid_lon"] = lon
        rec["centroid_lat"] = lat
        rec["geometry"] = mapping(geom)
        rec["last_seen_date"] = observation_date
        rec["area_ha_est"] = round(float(area_ha), 3)
        if props.get("agricultural_probability") is not None:
            rec["agricultural_probability"] = props["agricultural_probability"]
        if props.get("ag_class") is not None:
            rec["ag_class"] = props["ag_class"]
        rec["match_iou"] = round(best_iou, 4)
        return rec["aou_id"], rec

    aou_id = next_id(registry)
    rec = {
        "aou_id": aou_id,
        "previous_ids": [],
        "first_seen_date": observation_date,
        "last_seen_date": observation_date,
        "active": True,
        "centroid_lon": lon,
        "centroid_lat": lat,
        "geometry": mapping(geom),
        "area_ha_est": round(float(area_ha), 3),
        "agricultural_probability": props.get("agricultural_probability"),
        "ag_class": props.get("ag_class"),
        "region": REGION,
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§2",
    }
    registry.setdefault("units", []).append(rec)
    return aou_id, rec


def segment_probability_mask(
    cell_features: list[dict],
    *,
    prob_key: str = "agricultural_probability",
    min_prob: float = 60.0,
    soft_prob: float = 45.0,
    persistence_key: str = "persistence_gate",
    min_area_ha: float = MIN_AREA_HA,
) -> list[dict]:
    """Connected components on ~grid cells → AOU candidate polygons.

    Threshold: prob ≥ 60 OR (≥ 45 AND persistence gate).
    Uses 8-connect via shared/near boundaries (shapely touches/overlaps).
    Drops components < min_area_ha (~2 ha).
    """
    selected = []
    for f in cell_features:
        p = f.get("properties", {})
        prob = p.get(prob_key)
        if prob is None:
            continue
        gate = bool(p.get(persistence_key)) or float(prob) >= min_prob
        if float(prob) >= min_prob or (float(prob) >= soft_prob and gate):
            selected.append(f)

    if not selected:
        return []

    geoms = []
    metas = []
    for f in selected:
        g = shape(f["geometry"])
        if not g.is_valid:
            g = g.buffer(0)
        geoms.append(g)
        metas.append(f["properties"])

    # Union touching cells then explode to polygons
    merged = unary_union(geoms)
    parts = []
    if merged.geom_type == "Polygon":
        parts = [merged]
    elif merged.geom_type == "MultiPolygon":
        parts = list(merged.geoms)
    else:
        return []

    out = []
    for poly in parts:
        # area ha
        lon, lat = centroid_xy(poly)
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat))
        area_ha = abs(poly.area) * m_per_deg_lat * m_per_deg_lon / 10_000.0
        if area_ha < min_area_ha:
            continue
        # aggregate props from members that intersect
        member_props = [m for g, m in zip(geoms, metas) if poly.intersects(g)]
        probs = [m.get(prob_key) for m in member_props if m.get(prob_key) is not None]
        ndvis = [m.get("ndvi") for m in member_props if m.get("ndvi") is not None]
        ndmis = [m.get("ndmi") for m in member_props if m.get("ndmi") is not None]
        out.append(
            {
                "geometry": poly,
                "area_ha_est": round(area_ha, 3),
                "agricultural_probability": round(sum(probs) / len(probs), 2) if probs else None,
                "ndvi_mean": round(sum(ndvis) / len(ndvis), 4) if ndvis else None,
                "ndmi_mean": round(sum(ndmis) / len(ndmis), 4) if ndmis else None,
                "member_count": len(member_props),
                "cell_properties": member_props,
            }
        )
    return out
