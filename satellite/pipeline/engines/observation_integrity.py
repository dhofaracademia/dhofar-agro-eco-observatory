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
# Round-2 R2-2: numeric area gate (conservative = count fraction floor). Not null.
DEFAULT_MIN_VALID_AREA_FRACTION_AOU = 0.20

DISCOVERY_PROVISIONAL = "provisional_new"
DISCOVERY_ESTABLISHED = "established"


def discovery_status_for_n_clear(n_clear: int) -> str:
    """provisional_new until second clear date; then established."""
    return DISCOVERY_ESTABLISHED if int(n_clear or 0) >= 2 else DISCOVERY_PROVISIONAL


def cap_ag_class_for_discovery(ag_class: str | None, *, n_clear: int, discovery_status: str | None) -> str | None:
    """Day-1 / provisional: max possible; never likely/very_likely."""
    if ag_class is None:
        return None
    if discovery_status == DISCOVERY_PROVISIONAL or int(n_clear or 0) < 2:
        if ag_class in ("likely", "very_likely"):
            return "possible"
    return ag_class


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


def _member_clear_pixel_area_in_aou(m: dict[str, Any]) -> float:
    """Clear-pixel area inside AOU for one member (R3-1 + R4-1).

    Prefer ``aou_overlap_area × clear_fraction`` (clear footprint ∩ AOU estimate).
    Missing ``clear_fraction`` must **not** invent 1.0 / full-clear — contribute 0
    to the clear numerator (fail-honest). Unassessable → 0.
    """
    ov = m.get("aou_overlap_area")
    if ov is None:
        return 0.0
    try:
        a = float(ov)
    except (TypeError, ValueError):
        return 0.0
    if a <= 0:
        return 0.0
    cf = m.get("clear_fraction")
    if cf is None:
        # R4-1: no silent full-clear when coverage fraction absent
        return 0.0
    try:
        return a * max(0.0, min(1.0, float(cf)))
    except (TypeError, ValueError):
        return 0.0


def aou_assessability_with_area(
    members: list[dict],
    *,
    min_clear_fraction: float = DEFAULT_MIN_CLEAR_FRACTION_AOU,
    min_clear_members: int = DEFAULT_MIN_CLEAR_MEMBERS_AOU,
    min_valid_area_fraction: float | None = DEFAULT_MIN_VALID_AREA_FRACTION_AOU,
    aou_target_area: float | None = None,
) -> tuple[str, dict[str, Any]]:
    """AOU assessability with count + clear-pixel-in-AOU area fractions (R4-1).

    assessable_cell_fraction = clear assessable count / member count (secondary).
    valid_area_fraction = clear-pixel area inside AOU / denominator
      where clear-pixel area ≈ ∑(aou_overlap_area × clear_fraction)
      and denominator = aou_target_area (required for AOU-area honesty).
      Member-overlap sum is diagnostic only when target area is absent.
    Missing clear_fraction → exclude from numerator; stamp clear_fraction_missing.
    Basis stamp: valid_area_fraction_basis=clear_pixels_in_aou
      (or overlap_times_clear_fraction_estimate when all clear areas used that path).
    """
    meta = {
        "member_count": len(members),
        "clear_member_count": 0,
        "clear_member_fraction": 0.0,
        "assessable_cell_fraction": 0.0,
        "valid_area_fraction": None,
        "valid_area_fraction_basis": "clear_pixels_in_aou",
        "valid_area_fraction_denominator": None,
        "member_overlap_area_sum": 0.0,
        "clear_overlap_area_sum": 0.0,
        "clear_pixel_area_in_aou_sum": 0.0,
        "clear_fraction_missing": False,
        "coverage_incomplete": False,
        "min_clear_fraction_aou": min_clear_fraction,
        "min_clear_members_aou": min_clear_members,
        "min_valid_area_fraction_aou": min_valid_area_fraction,
        "aou_target_area": aou_target_area,
    }
    if not members:
        return "unassessable", meta

    clear = [m for m in members if cell_assessability(m) == "assessable"]
    meta["clear_member_count"] = len(clear)
    frac_count = len(clear) / max(len(members), 1)
    meta["clear_member_fraction"] = frac_count
    meta["assessable_cell_fraction"] = frac_count
    # Do NOT set clear_fraction=count_frac yet — R4-1: never publish
    # clear_fraction=1.0 together with clear_fraction_missing=True.
    meta["clear_fraction"] = None

    area_all = 0.0
    area_clear_polygon = 0.0  # legacy full-polygon (secondary diagnostic only)
    clear_pixel_area = 0.0
    any_cf_missing = False
    any_cf_used = False
    cf_weight_sum = 0.0
    cf_area_sum = 0.0
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
            area_clear_polygon += a
        if m.get("clear_fraction") is None:
            any_cf_missing = True
        else:
            any_cf_used = True
            try:
                cfv = max(0.0, min(1.0, float(m["clear_fraction"])))
                cf_weight_sum += a * cfv
                cf_area_sum += a
            except (TypeError, ValueError):
                any_cf_missing = True
        clear_pixel_area += _member_clear_pixel_area_in_aou(m)
    meta["member_overlap_area_sum"] = area_all
    meta["clear_overlap_area_sum"] = area_clear_polygon
    meta["clear_pixel_area_in_aou_sum"] = clear_pixel_area
    meta["clear_fraction_missing"] = bool(any_cf_missing)
    meta["coverage_incomplete"] = bool(any_cf_missing)
    if any_cf_missing:
        # Honest: missing cell clear_fraction → no invented 1.0 alias
        meta["clear_fraction"] = None
    elif cf_area_sum > 0:
        meta["clear_fraction"] = round(cf_weight_sum / cf_area_sum, 6)
    else:
        # All clear_fractions present but no overlap areas — count alias only
        meta["clear_fraction"] = frac_count
    if any_cf_used and not any_cf_missing:
        meta["valid_area_fraction_basis"] = "overlap_times_clear_fraction_estimate"
    else:
        meta["valid_area_fraction_basis"] = "clear_pixels_in_aou"

    denom = None
    denom_kind = None
    if aou_target_area is not None:
        try:
            ta = float(aou_target_area)
        except (TypeError, ValueError):
            ta = 0.0
        if ta > 0:
            denom = ta
            denom_kind = "aou_target_area"
    if denom is None and area_all > 0:
        # Diagnostic fallback only — callers must pass aou_target_area for honesty
        denom = area_all
        denom_kind = "member_overlap_sum"
    meta["valid_area_fraction_denominator"] = denom_kind
    if denom is not None and denom > 0:
        # Cap at 1.0 — overlaps must not report >100%
        frac = clear_pixel_area / denom
        meta["valid_area_fraction"] = min(1.0, float(frac))
    else:
        meta["valid_area_fraction"] = None

    count_fail = len(clear) < int(min_clear_members) or frac_count < float(min_clear_fraction)
    area_fail = False
    if min_valid_area_fraction is not None:
        if meta["valid_area_fraction"] is None:
            # Missing coverage / no area → do not auto-accept
            area_fail = True
        else:
            area_fail = float(meta["valid_area_fraction"]) < float(min_valid_area_fraction)
    # When area threshold set, both count and area must pass; missing area fails.
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
            "valid_area_fraction_basis": assess_meta.get(
                "valid_area_fraction_basis", "clear_pixels_in_aou"
            ),
            "valid_area_fraction_denominator": assess_meta.get("valid_area_fraction_denominator"),
            "clear_member_fraction": assess_meta.get("clear_member_fraction"),
        },
    }


# --- Post-#29 R3-3: all-or-nothing promote with full rollback ---
def atomic_promote_with_rollback(
    *,
    stage_root: "Path",
    public_root: "Path",
    relative_paths: list[str],
    fail_after: int | None = None,
) -> None:
    """Promote staged files to public with last-good snapshot + full rollback.

    1. Snapshot every existing public file in ``relative_paths``.
    2. Move staged files into public one-by-one.
    3. On any mid-promote error (or injected ``fail_after``): restore **all**
       moved paths from the snapshot (or delete if no last-good). Partner never
       sees a partial new release (e.g. latest_alerts+timeseries half-update).
    """
    import shutil
    import tempfile
    from pathlib import Path

    stage_root = Path(stage_root)
    public_root = Path(public_root)
    snapshot = Path(
        tempfile.mkdtemp(prefix="publish_last_good_", dir=str(public_root.parent))
    )
    moved: list[str] = []
    try:
        for rel in relative_paths:
            dst = public_root / rel
            if dst.is_file():
                snap = snapshot / rel
                snap.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, snap)
        for i, rel in enumerate(relative_paths):
            if fail_after is not None and i >= int(fail_after):
                raise RuntimeError(
                    f"injected promote failure after {fail_after} moves ({rel})"
                )
            src = stage_root / rel
            if not src.exists():
                raise FileNotFoundError(f"staged release missing {rel}")
            dst = public_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved.append(rel)
    except Exception:
        restore_ok = True
        for rel in moved:
            dst = public_root / rel
            snap = snapshot / rel
            try:
                if snap.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(snap, dst)
                elif dst.exists():
                    try:
                        dst.unlink()
                    except OSError:
                        restore_ok = False
            except OSError:
                restore_ok = False
        if not restore_ok:
            # Never delete backup if restore failed — keep snapshot for manual recovery
            raise
        shutil.rmtree(snapshot, ignore_errors=True)
        raise
    else:
        shutil.rmtree(snapshot, ignore_errors=True)
    finally:
        # Only remove snapshot on success path (handled in else) or clean unused snap
        if not moved and snapshot.exists():
            shutil.rmtree(snapshot, ignore_errors=True)



def aou_geometry_target_area(geom: Any, *, area_ha_est: float | None = None) -> float | None:
    """AOU target area in geometry CRS units (deg²) or projected m² — consistent with overlap.

    Prefer shapely geometry ``.area`` so units match ``aou_overlap_area`` from
    ``positive_area_overlap``. ``area_ha_est`` is a fallback when geom area is
    unavailable (converted assuming geographic approx is unacceptable — only
    used when geom.area is 0/None and ha is provided via projected estimate).
    """
    if geom is not None:
        try:
            a = float(geom.area)
            if a > 0:
                return a
        except Exception:
            pass
    if area_ha_est is not None:
        try:
            ha = float(area_ha_est)
        except (TypeError, ValueError):
            return None
        if ha > 0:
            # Keep as ha→m² only when overlaps are also in m²; callers using
            # geographic overlap should pass geom.area. Stamp via area_ha path
            # is diagnostic — return None rather than mix units silently.
            return None
    return None


def verify_release_ids_match(
    root: "Path",
    release_id: str,
    relative_paths: list[str] | None = None,
) -> list[str]:
    """Pre-promote gate (R4-4): every listed artifact must carry identical release_id.

    Returns list of failure messages (empty = OK).
    """
    from pathlib import Path
    import json

    root = Path(root)
    rels = relative_paths or [
        "meta/run_meta.json",
        "meta/last_refresh.json",
        "timeseries.json",
        "latest_alerts.geojson",
        "aou/aou_observations.json",
        "aou/aou_registry.json",
        "aou/aou_registry.geojson",
        "decision/run_meta.json",
        "decision/aou_confidence.json",
        "decision/aou_suitability_components.json",
        "decision/aou_evidence_gaps.json",
    ]
    failures: list[str] = []
    for rel in rels:
        p = root / rel
        if not p.is_file():
            # Optional decision files may be absent on standalone skip path
            if rel.startswith("decision/"):
                continue
            failures.append(f"missing:{rel}")
            continue
        try:
            doc = json.loads(p.read_text())
        except Exception as e:
            failures.append(f"invalid_json:{rel}:{e}")
            continue
        rid = doc.get("release_id")
        if rid is None and isinstance(doc.get("properties"), dict):
            rid = doc["properties"].get("release_id")
        if rid is None and isinstance(doc.get("meta"), dict):
            rid = doc["meta"].get("release_id")
        # Registry list shape
        if rid is None and isinstance(doc.get("units"), list) and doc.get("release_id") is None:
            rid = doc.get("release_id")
        if rid != release_id:
            failures.append(f"id_mismatch:{rel}:got={rid!r}:want={release_id!r}")
    return failures


def publish_release_with_pointer(
    *, stage_root: "Path", public_root: "Path", release_id: str,
    relative_paths: list[str], fail_before_pointer: bool = False,
    fail_mid_copy: int | None = None,
) -> "Path":
    """Publish a new immutable tree, then transactionally mirror files + pointers.

    Frontends pin latest_release.json once per session. Existing release IDs
    are never replaced. Legacy files and pointers share rollback on failure.
    """
    import json
    import re
    import shutil
    import tempfile
    from pathlib import Path

    if not re.fullmatch(r"[A-Za-z0-9_-]+", release_id):
        raise ValueError("Invalid release id")
    stage_root, public_root = Path(stage_root), Path(public_root)
    releases = public_root / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    release_dir = releases / release_id
    if release_dir.exists():
        raise FileExistsError(f"Immutable release already exists: {release_id}")
    rels = list(dict.fromkeys(relative_paths))
    for rel in rels:
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ValueError(f"Invalid release path: {rel}")
    pending = Path(tempfile.mkdtemp(prefix=".pending-", dir=releases))
    try:
        for i, rel in enumerate(rels):
            if fail_mid_copy is not None and i >= fail_mid_copy:
                raise RuntimeError(f"injected mid-copy failure at {rel}")
            src, dst = stage_root / rel, pending / rel
            if not src.is_file():
                raise FileNotFoundError(f"staged release missing {rel}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        if fail_before_pointer:
            raise RuntimeError("injected failure before pointer swap")
        pending.rename(release_dir)
        pointer_doc = {
            "release_id": release_id, "path": f"releases/{release_id}",
            "artifacts": rels, "pointer_semantics": "immutable_release_dir_plus_current",
            "atomic_claim": False,
        }
        (stage_root / "latest_release.json").write_text(json.dumps(pointer_doc, indent=2))
        (stage_root / "CURRENT").write_text(release_id + "\n")
        atomic_promote_with_rollback(
            stage_root=stage_root, public_root=public_root,
            relative_paths=rels + ["CURRENT", "latest_release.json"],
        )
        # Compatibility only; the web app uses latest_release.json, never this link.
        link = public_root / "CURRENT_LINK"
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(Path("releases") / release_id)
        except OSError:
            pass
        return release_dir
    finally:
        shutil.rmtree(pending, ignore_errors=True)


def stamp_release_id_on_doc(doc: dict[str, Any], release_id: str) -> dict[str, Any]:
    """Stamp identical release_id/run_id on a JSON document (R4-4)."""
    doc["release_id"] = release_id
    doc["run_id"] = release_id
    if isinstance(doc.get("properties"), dict):
        doc["properties"]["release_id"] = release_id
        doc["properties"]["run_id"] = release_id
    return doc

def safe_relpath(path, root) -> str:
    """Return path relative to root, or absolute str if outside root (no throw)."""
    from pathlib import Path
    p = Path(path).resolve()
    r = Path(root).resolve()
    try:
        return str(p.relative_to(r))
    except ValueError:
        return str(p)
