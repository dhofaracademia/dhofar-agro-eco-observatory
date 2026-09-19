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


# --- Post-integrity evaluator: per-cell / per-AOU clear coverage (§1) ---
# Thresholds stamped in run_meta by callers.
DEFAULT_MIN_CLEAR_PIXELS_CELL = 50
DEFAULT_MIN_CLEAR_FRACTION_CELL = 0.02
DEFAULT_MIN_CLEAR_FRACTION_AOU = 0.20
DEFAULT_MIN_CLEAR_MEMBERS_AOU = 1


def cell_assessability(
    props: dict[str, Any],
    *,
    min_clear_pixels: int = DEFAULT_MIN_CLEAR_PIXELS_CELL,
    min_clear_fraction: float = DEFAULT_MIN_CLEAR_FRACTION_CELL,
) -> str:
    """Per-cell clear-coverage gate. Scene clear alone is not sufficient.

    Missing SCL / cloudlike / below threshold → unassessable (never invent NDVI/NDMI).
    """
    if props.get("scl_missing") is True or props.get("scl_status") == "missing":
        return "unassessable"
    if props.get("scl_clear") is False:
        return "unassessable"
    status = props.get("status") or props.get("coverage_status")
    if status in ("unclassified", "blocked", "scl_missing", "coverage_fail"):
        return "unassessable"
    pc = props.get("pixel_count")
    if pc is not None and int(pc) < int(min_clear_pixels):
        return "unassessable"
    frac = props.get("clear_fraction")
    if frac is not None and float(frac) < float(min_clear_fraction):
        return "unassessable"
    # No valid optical reading → cannot vote
    if props.get("ndvi") is None or props.get("ndmi") is None:
        return "unassessable"
    return "assessable"


def aou_assessability(
    members: list[dict],
    *,
    min_clear_fraction: float = DEFAULT_MIN_CLEAR_FRACTION_AOU,
    min_clear_members: int = DEFAULT_MIN_CLEAR_MEMBERS_AOU,
) -> tuple[str, dict[str, Any]]:
    """Per-AOU clear-coverage after positive-area join.

    clear-coverage = clear assessable members / in-AOU members (count basis).
    Below threshold → unassessable for that date (do not advance observation_date).
    """
    meta = {
        "member_count": len(members),
        "clear_member_count": 0,
        "clear_fraction": 0.0,
        "min_clear_fraction_aou": min_clear_fraction,
        "min_clear_members_aou": min_clear_members,
    }
    if not members:
        return "unassessable", meta
    clear = [m for m in members if cell_assessability(m) == "assessable"]
    meta["clear_member_count"] = len(clear)
    meta["clear_fraction"] = len(clear) / max(len(members), 1)
    if len(clear) < int(min_clear_members) or meta["clear_fraction"] < float(min_clear_fraction):
        return "unassessable", meta
    return "assessable", meta


def ledger_sequence_rows(unit_or_obs: dict[str, Any] | None) -> list[dict]:
    """AOU ledger clear-date rows only (exclude window_not_aou). Ordered by date."""
    if not unit_or_obs:
        return []
    rows = []
    for o in unit_or_obs.get("observations") or []:
        if o.get("series_scope") == "window_not_aou":
            continue
        if not o.get("date"):
            continue
        if o.get("ndvi") is None:
            continue
        rows.append(o)
    rows.sort(key=lambda r: str(r["date"]))
    return rows


def ledger_persistence_feature(
    rows: list[dict],
    *,
    bare_ndvi: float = 0.18,
) -> tuple[float | None, int, int]:
    """Persistence from ledger clear-date sequence only.

    Forbidden: invent 0.5 solely because n_clear >= 2 without sequence feature.
    n_clear < 2 → None (caller renorms / gates).
    """
    n_clear = len(rows)
    if n_clear < 2:
        return None, n_clear, 0
    n_above = sum(1 for r in rows if float(r.get("ndvi") or -1) >= bare_ndvi)
    frac = n_above / max(n_clear, 1)
    if n_above < 2:
        return max(0.0, min(1.0, frac * 0.5)), n_clear, n_above
    return max(0.0, min(1.0, frac)), n_clear, n_above


def ledger_stress_flags(
    rows: list[dict],
    *,
    kind: str,
    last_n: int = 3,
    attention_thr: float = 55.0,
) -> list[bool]:
    """Derive recent stress flags from ledger sequence — never invent 'healthy' from []."""
    recent = rows[-last_n:] if rows else []
    flags: list[bool] = []
    for r in recent:
        if kind == "water":
            score = r.get("water_stress_score")
            alert = r.get("alert")
            flags.append(
                bool(alert == "water_attention")
                or (score is not None and float(score) >= attention_thr)
            )
        else:
            score = r.get("vigor_stress_score")
            alert = r.get("alert")
            flags.append(
                bool(alert == "vigor_attention")
                or (score is not None and float(score) >= attention_thr)
            )
    return flags

