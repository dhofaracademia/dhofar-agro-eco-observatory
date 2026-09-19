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



# --- Evaluator deep re-check (SCIENCE_LOCKS_v0.4_evaluator_deep_recheck) ---
OBSERVATION_ROLE_CURRENT = "current_observation"
OBSERVATION_ROLE_RETAINED = "retained_last_good"
BIOTIC_POSSIBLE = "possible"
BIOTIC_UNKNOWN = "unknown"
BIOTIC_NOT_FLAGGED = "not_flagged"


def ledger_rows_before(
    unit_or_obs: dict[str, Any] | None,
    before_date: str | None,
) -> list[dict]:
    """Ledger clear-date rows with date < before_date (strict). None before_date → all."""
    rows = ledger_sequence_rows(unit_or_obs)
    if not before_date:
        return rows
    return [r for r in rows if str(r.get("date") or "") < str(before_date)]


def ledger_rows_excluding_date(
    unit_or_obs: dict[str, Any] | None,
    exclude_date: str | None,
) -> list[dict]:
    """Ledger rows excluding same-day T (replace without treating T as prior evidence)."""
    rows = ledger_sequence_rows(unit_or_obs)
    if not exclude_date:
        return rows
    return [r for r in rows if str(r.get("date") or "") != str(exclude_date)]


def observation_role_for_refresh(refresh_status: str | None, *, has_new: bool) -> str:
    """current_observation only when this run advanced a clear assessable sample."""
    if has_new and refresh_status == "refreshed":
        return OBSERVATION_ROLE_CURRENT
    return OBSERVATION_ROLE_RETAINED


def biotic_status_three_state(
    *,
    possible_biotic_stress: bool,
    n_clear: int,
    rules_evaluated: bool = True,
) -> str:
    """possible | unknown | not_flagged — never confirmed pest; silence ≠ healthy."""
    if possible_biotic_stress:
        return BIOTIC_POSSIBLE
    if n_clear < 2 or not rules_evaluated:
        return BIOTIC_UNKNOWN
    return BIOTIC_NOT_FLAGGED


def aou_assessability_with_area(
    members: list[dict],
    *,
    min_clear_fraction: float = DEFAULT_MIN_CLEAR_FRACTION_AOU,
    min_clear_members: int = DEFAULT_MIN_CLEAR_MEMBERS_AOU,
    min_valid_area_fraction: float | None = None,
) -> tuple[str, dict[str, Any]]:
    """AOU assessability with count + area fractions.

    assessable_cell_fraction = clear assessable count / member count (secondary).
    valid_area_fraction = sum(overlap of assessable clear) / sum(overlap of all members).
    Primary gate may use either; area is stamped always when overlaps present.
    """
    meta = {
        "member_count": len(members),
        "clear_member_count": 0,
        "clear_member_fraction": 0.0,
        "assessable_cell_fraction": 0.0,
        "valid_area_fraction": None,
        "member_overlap_area_sum": 0.0,
        "clear_overlap_area_sum": 0.0,
        "min_clear_fraction_aou": min_clear_fraction,
        "min_clear_members_aou": min_clear_members,
        "min_valid_area_fraction_aou": min_valid_area_fraction,
    }
    if not members:
        return "unassessable", meta

    clear = [m for m in members if cell_assessability(m) == "assessable"]
    meta["clear_member_count"] = len(clear)
    frac_count = len(clear) / max(len(members), 1)
    meta["clear_member_fraction"] = frac_count
    meta["assessable_cell_fraction"] = frac_count
    # Backward-compat alias used by older callers / UI
    meta["clear_fraction"] = frac_count

    area_all = 0.0
    area_clear = 0.0
    for m in members:
        ov = m.get("aou_overlap_area")
        if ov is None:
            continue
        try:
            a = float(ov)
        except (TypeError, ValueError):
            continue
        if a <= 0:
            continue
        area_all += a
        if cell_assessability(m) == "assessable":
            area_clear += a
    meta["member_overlap_area_sum"] = area_all
    meta["clear_overlap_area_sum"] = area_clear
    if area_all > 0:
        meta["valid_area_fraction"] = area_clear / area_all
    else:
        meta["valid_area_fraction"] = None

    count_fail = len(clear) < int(min_clear_members) or frac_count < float(min_clear_fraction)
    area_fail = False
    if min_valid_area_fraction is not None and meta["valid_area_fraction"] is not None:
        area_fail = float(meta["valid_area_fraction"]) < float(min_valid_area_fraction)
    # When area available and threshold set, both must pass; else count gate alone.
    if count_fail or area_fail:
        return "unassessable", meta
    return "assessable", meta


def build_aou_date_aggregate(
    *,
    aou_id: str,
    date: str | None,
    clear_members: list[dict],
    all_members: list[dict],
    assessability: str,
    assess_meta: dict[str, Any],
    run_id: str | None = None,
    water_stress: float | None = None,
    vigor_stress: float | None = None,
    alert: str | None = None,
    agricultural_probability: float | None = None,
    ag_class: str | None = None,
    persistence_feature: float | None = None,
    n_clear_dates: int | None = None,
    n_dates_above_bare: int | None = None,
    observation_role: str | None = None,
    biotic_status: str | None = None,
    possible_biotic_stress: bool | None = None,
    refresh_status: str | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Single frozen (AOU, date) aggregate consumed by registry, ledger, decision."""
    mean_ndvi, mean_ndmi = member_clear_means(clear_members)
    accepted = [
        {
            "ndvi": m.get("ndvi"),
            "ndmi": m.get("ndmi"),
            "pixel_count": m.get("pixel_count"),
            "aou_overlap_area": m.get("aou_overlap_area"),
            "product_id": m.get("product_id"),
        }
        for m in clear_members
    ]
    srcs = sources or sorted(
        {str(m.get("source") or m.get("product_id") or "") for m in clear_members if m.get("source") or m.get("product_id")}
    )
    aggregate_id = f"{aou_id}|{date or 'none'}|{run_id or 'norun'}"
    return {
        "aggregate_id": aggregate_id,
        "aou_id": aou_id,
        "date": date,
        "run_id": run_id,
        "ndvi": None if mean_ndvi is None else round(float(mean_ndvi), 4),
        "ndmi": None if mean_ndmi is None else round(float(mean_ndmi), 4),
        "water_stress_score": water_stress,
        "vigor_stress_score": vigor_stress,
        "alert": alert,
        "agricultural_probability": agricultural_probability,
        "ag_class": ag_class,
        "persistence_feature": persistence_feature,
        "n_clear_dates": n_clear_dates,
        "n_dates_above_bare": n_dates_above_bare,
        "assessability": assessability,
        "assessable_cell_fraction": assess_meta.get("assessable_cell_fraction"),
        "valid_area_fraction": assess_meta.get("valid_area_fraction"),
        "clear_member_fraction": assess_meta.get("clear_member_fraction"),
        "clear_member_count": assess_meta.get("clear_member_count"),
        "member_count": assess_meta.get("member_count", len(all_members)),
        "observation_role": observation_role,
        "biotic_status": biotic_status,
        "possible_biotic_stress": possible_biotic_stress,
        "refresh_status": refresh_status,
        "accepted_cells": accepted,
        "sources": [s for s in srcs if s],
        "coverage": {
            "assessable_cell_fraction": assess_meta.get("assessable_cell_fraction"),
            "valid_area_fraction": assess_meta.get("valid_area_fraction"),
            "clear_member_fraction": assess_meta.get("clear_member_fraction"),
        },
    }
