"""Observation integrity helpers — SCIENCE_LOCKS_v0.4_observation_integrity.md

Positive-area cell→AOU join, alert/timeseries consistency, publish gates.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from shapely.geometry import shape

# Declared multi-AOU rule (stamped in run_meta). Alternative: area_weighted.
JOIN_RULE = "max_overlap_area"
# Drop boundary-only / numerical dust touches (deg²; ~1 m² at ~18N is ~1e-10)
AREA_EPS = 1e-12

TEMPORAL_EVIDENCE_INSUFFICIENT_AR = "أدلة زمنية غير كافية"
TEMPORAL_EVIDENCE_INSUFFICIENT_EN = "Insufficient temporal evidence"


def positive_area_overlap(a, b, *, eps: float = AREA_EPS) -> float:
    """Return intersection area if > eps; else 0 (rejects boundary-only intersects)."""
    try:
        if a is None or b is None or a.is_empty or b.is_empty:
            return 0.0
        if not a.intersects(b):
            return 0.0
        inter = a.intersection(b)
        if inter.is_empty:
            return 0.0
        area = float(inter.area)
        return area if area > eps else 0.0
    except Exception:
        return 0.0


def clear_cell_aou_ids(features: list[dict]) -> None:
    """Clear prior cell→AOU assignments before reassign (no stale IDs)."""
    for f in features:
        props = f.setdefault("properties", {})
        props["aou_id"] = None


def assign_cells_max_overlap(
    features: list[dict],
    aou_geoms: list[tuple[str, Any]],
    *,
    bare_ndvi: float = 0.18,
) -> dict[str, dict[str, Any]]:
    """Assign each cell to at most one AOU by max positive-area overlap.

    Returns per-AOU: {members, vegetated, overlap_areas}.
    Touch-only (zero area) cells are dropped. Multi-hit → max overlap wins.
    """
    clear_cell_aou_ids(features)
    # cell_idx -> (aou_id, overlap_area)
    best: dict[int, tuple[str, float]] = {}
    for aou_id, geom in aou_geoms:
        if geom is None:
            continue
        for i, f in enumerate(features):
            try:
                g = shape(f["geometry"])
            except Exception:
                continue
            ov = positive_area_overlap(geom, g)
            if ov <= 0:
                continue
            prev = best.get(i)
            if prev is None or ov > prev[1]:
                best[i] = (aou_id, ov)

    by_aou: dict[str, dict[str, Any]] = {
        aid: {"members": [], "vegetated": [], "member_indices": [], "overlap_total": 0.0}
        for aid, _ in aou_geoms
    }
    for i, (aou_id, ov) in best.items():
        f = features[i]
        f["properties"]["aou_id"] = aou_id
        f["properties"]["aou_overlap_area"] = ov
        props = f["properties"]
        bucket = by_aou.setdefault(
            aou_id,
            {"members": [], "vegetated": [], "member_indices": [], "overlap_total": 0.0},
        )
        bucket["members"].append(props)
        bucket["member_indices"].append(i)
        bucket["overlap_total"] += ov
        if (props.get("ndvi") or 0) >= bare_ndvi and props.get("ndvi") is not None:
            bucket["vegetated"].append(props)
    return by_aou


def member_clear_means(members: list[dict]) -> tuple[float | None, float | None]:
    """Mean NDVI/NDMI from members that have both valid readings."""
    pairs = [
        (m["ndvi"], m["ndmi"])
        for m in members
        if m.get("ndvi") is not None and m.get("ndmi") is not None
    ]
    if not pairs:
        return None, None
    ndvi = sum(p[0] for p in pairs) / len(pairs)
    ndmi = sum(p[1] for p in pairs) / len(pairs)
    return float(ndvi), float(ndmi)


def count_alerts(features: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for f in features:
        counts[str(f.get("properties", {}).get("alert") or "unclear")] += 1
    return dict(counts)


def alert_counts_match(a: dict[str, int], b: dict[str, int]) -> bool:
    keys = set(a) | set(b)
    return all(int(a.get(k, 0)) == int(b.get(k, 0)) for k in keys)


def temporal_evidence_labels(n_clear: int) -> dict[str, Any]:
    """Empty / single-date stress-biotic history ≠ 'no biotic issue'."""
    insufficient = n_clear < 2
    return {
        "temporal_evidence_sufficient": not insufficient,
        "temporal_evidence_ar": TEMPORAL_EVIDENCE_INSUFFICIENT_AR if insufficient else None,
        "temporal_evidence_en": TEMPORAL_EVIDENCE_INSUFFICIENT_EN if insufficient else None,
        "biotic_unknown_reason": "insufficient_temporal_evidence" if insufficient else None,
    }
