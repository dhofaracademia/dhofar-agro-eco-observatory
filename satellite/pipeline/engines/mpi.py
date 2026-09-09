"""
Moisture Persistence Index (MPI) — Phase-2 offline helpers.

Binding: docs/SCIENCE_LOCKS_v0.4_phase1_2.md §5

- T0 = first clear post-onset OR post-khareef reference (dynamic; documented).
- Samples: T0, T+1w, T+2w, T+4w, T+6w clear Sentinel-2 NDMI.
- Gaps → null; never interpolate fabricated NDMI.
- Classes: High / Medium / Low / Insufficient (<2 valid → no class).
- NDMI / MPI are moisture *proxies*, NOT soil moisture %.
- Stamp outputs pilot_unverified + provisional until field validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np

# SCIENCE_LOCKS §5.2 expert defaults (calibrate later with field data)
MPI_LAGS_WEEKS = (0, 1, 2, 4, 6)
MPI_SEARCH_HALF_WINDOW_DAYS = 3  # multi-scene ±3d of T+N

# Dry baseline for mountain AOI — NDMI at/near bare / arid floor (proxy, not %)
DEFAULT_DRY_BASELINE_NDMI = -0.05

LAYER_MPI = "mountain_mpi_phase2"
STATUS_PILOT = "pilot_unverified"
STATUS_INSUFFICIENT = "insufficient_clear_data"

# Partner-facing / terrain-layer forbidden keys (science lock table).
# Offline mpi_cells MAY carry mpi_class + provisional stamps; must NOT carry
# suitability scores, action auto-assign, species, or soil_moisture_pct.
FORBIDDEN_PARTNER_KEYS = {
    "suitability",
    "suitability_score",
    "species_suitability",
    "confidence",
    "ecological_confidence",
    "action",
    "action_ladder",
    "regeneration_action",
    "species",
    "species_note",
    "soil_moisture",
    "soil_moisture_pct",
    "soil_moisture_percent",
    "campaign_ha",
    "seed_kg",
    "crew_days",
}


@dataclass
class MpiSamplePoint:
    lag_weeks: int
    target_date: date
    search_range: str
    ndmi_mean: float | None
    status: str  # ok | gap | insufficient_clear_data
    product_id: str | None = None
    scene_date: str | None = None
    tile: str | None = None
    cloud_cover: float | None = None
    clear_frac: float | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lag_weeks": self.lag_weeks,
            "target_date": self.target_date.isoformat(),
            "search_range": self.search_range,
            "ndmi_mean": self.ndmi_mean,
            "status": self.status,
            "product_id": self.product_id,
            "scene_date": self.scene_date,
            "tile": self.tile,
            "cloud_cover": self.cloud_cover,
            "clear_frac": self.clear_frac,
            "reason": self.reason,
        }


@dataclass
class MpiCurveResult:
    t0_date: date | None
    t0_method: str
    points: list[MpiSamplePoint] = field(default_factory=list)
    mpi_class: str | None = None  # High|Medium|Low|None when Insufficient
    mpi_class_reason: str = ""
    n_valid: int = 0
    dry_baseline_ndmi: float = DEFAULT_DRY_BASELINE_NDMI
    status: str = STATUS_PILOT
    provisional: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "t0_date": self.t0_date.isoformat() if self.t0_date else None,
            "t0_method": self.t0_method,
            "points": [p.to_dict() for p in self.points],
            "mpi_class": self.mpi_class,
            "mpi_class_reason": self.mpi_class_reason,
            "n_valid": self.n_valid,
            "dry_baseline_ndmi": self.dry_baseline_ndmi,
            "status": self.status,
            "provisional": self.provisional,
            "disclaimer_en": (
                "NDMI and MPI are satellite moisture proxies, not soil moisture %. "
                "Classes are provisional / pilot_unverified until field validation."
            ),
        }


def parse_iso_date(s: str) -> date:
    return date.fromisoformat(s[:10])


def date_window(center: date, half_days: int = MPI_SEARCH_HALF_WINDOW_DAYS) -> str:
    lo = center - timedelta(days=half_days)
    hi = center + timedelta(days=half_days)
    return f"{lo.isoformat()}/{hi.isoformat()}"


def classify_mpi(
    ndmi_by_lag: dict[int, float | None],
    dry_baseline: float = DEFAULT_DRY_BASELINE_NDMI,
) -> tuple[str | None, str, int]:
    """
    SCIENCE_LOCKS §5.2:
      High         ≥3 valid; NDMI stays above dry baseline through T+4 or slow decay
      Medium       2–3 valid; mixed / moderate decay
      Low          Rapid return to dry baseline by T+2, or only T0 wet
      Insufficient <2 valid clear points → no class (fail-honest)
    Returns (class_or_None, reason, n_valid).
    """
    valid_lags = sorted(k for k, v in ndmi_by_lag.items() if v is not None and np.isfinite(v))
    n_valid = len(valid_lags)
    if n_valid < 2:
        return None, f"Insufficient: {n_valid} valid clear point(s) < 2 (fail-honest; no class)", n_valid

    vals = {k: float(ndmi_by_lag[k]) for k in valid_lags}
    t0 = vals.get(0)
    above_through_t4 = all(
        vals[k] > dry_baseline for k in valid_lags if k <= 4
    ) and any(k >= 4 for k in valid_lags) and n_valid >= 3

    # Slow decay: if we have T0 and a later point, drop per week is mild
    later = [k for k in valid_lags if k > 0]
    slow_decay = False
    if t0 is not None and later:
        k_last = max(later)
        drop = t0 - vals[k_last]
        weeks = max(k_last, 1)
        slow_decay = (drop / weeks) <= 0.03 and vals[k_last] > dry_baseline

    # Rapid return by T+2
    rapid = False
    if 2 in vals and t0 is not None:
        rapid = vals[2] <= dry_baseline and t0 > dry_baseline
    elif later and t0 is not None:
        early_later = [k for k in later if k <= 2]
        if early_later:
            rapid = vals[min(early_later)] <= dry_baseline and t0 > dry_baseline

    only_t0_wet = (
        t0 is not None
        and t0 > dry_baseline
        and all(vals[k] <= dry_baseline for k in valid_lags if k > 0)
    )
    all_dry = all(vals[k] <= dry_baseline for k in valid_lags)

    if n_valid >= 3 and (above_through_t4 or slow_decay):
        return "High", "≥3 valid; above baseline through T+4 or slow decay (provisional)", n_valid
    if rapid or only_t0_wet or all_dry:
        reason = (
            "All valid NDMI ≤ dry baseline (no persistence signal; provisional)"
            if all_dry and not (rapid or only_t0_wet)
            else "Rapid return to dry baseline by T+2, or only T0 wet (provisional)"
        )
        return "Low", reason, n_valid
    if n_valid >= 2:
        return "Medium", "2–3+ valid with mixed / moderate decay (provisional)", n_valid
    return None, "Insufficient (fallback)", n_valid


def assert_no_forbidden_partner_keys(props: dict[str, Any]) -> None:
    bad = FORBIDDEN_PARTNER_KEYS.intersection(props.keys())
    if bad:
        raise RuntimeError(f"Forbidden partner-facing properties: {sorted(bad)}")


def stratified_sample_indices(
    elevations: np.ndarray,
    slopes: np.ndarray,
    n_total: int = 48,
    elev_bins: int = 3,
    slope_bins: int = 2,
    rng_seed: int = 42,
) -> list[int]:
    """
    Stratified sample across elevation tertiles × slope (gentle/steep).
    Not first-N high-elev only.
    """
    n = len(elevations)
    if n == 0:
        return []
    if n <= n_total:
        return list(range(n))

    elev = np.asarray(elevations, dtype="float64")
    slope = np.asarray(slopes, dtype="float64")
    finite = np.isfinite(elev) & np.isfinite(slope)
    idx_all = np.arange(n)

    # Elevation tertile edges from finite values
    fe = elev[finite]
    fs = slope[finite]
    if fe.size == 0:
        return list(range(min(n_total, n)))

    elev_edges = np.quantile(fe, np.linspace(0, 1, elev_bins + 1))
    slope_med = float(np.median(fs))

    strata: dict[tuple[int, int], list[int]] = {}
    for i in idx_all:
        if not finite[i]:
            continue
        # bin elev
        ebin = int(np.searchsorted(elev_edges[1:-1], elev[i], side="right"))
        ebin = min(max(ebin, 0), elev_bins - 1)
        sbin = 0 if slope[i] < slope_med else 1
        strata.setdefault((ebin, sbin), []).append(int(i))

    rng = np.random.default_rng(rng_seed)
    per = max(1, n_total // max(1, len(strata)))
    chosen: list[int] = []
    # Round-robin so each stratum gets representation
    for key in sorted(strata.keys()):
        pool = strata[key]
        take = min(per, len(pool))
        pick = rng.choice(pool, size=take, replace=False).tolist()
        chosen.extend(int(x) for x in pick)

    # Fill up if short
    if len(chosen) < n_total:
        remaining = [i for i in idx_all.tolist() if i not in set(chosen)]
        need = n_total - len(chosen)
        if remaining:
            extra = rng.choice(remaining, size=min(need, len(remaining)), replace=False).tolist()
            chosen.extend(int(x) for x in extra)

    return chosen[:n_total]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Natural Regeneration ladder (SCIENCE_LOCKS §6) — enum + rule stubs ONLY ---

REGENERATION_LADDER_ENUM = [
    "protect_natural_regeneration",
    "assisted_natural_regeneration",
    "enrichment_seeding",
    "active_planting",
    "avoid_defer",
]

REGENERATION_LADDER_LABELS = {
    "protect_natural_regeneration": {
        "en": "Protect Natural Regeneration",
        "ar": "حماية التجدد الطبيعي",
        "order": 1,
    },
    "assisted_natural_regeneration": {
        "en": "Assisted Natural Regeneration",
        "ar": "تجدد طبيعي مُساعَد",
        "order": 2,
    },
    "enrichment_seeding": {
        "en": "Enrichment Seeding",
        "ar": "بذر إثرائي",
        "order": 3,
    },
    "active_planting": {
        "en": "Active Planting",
        "ar": "زراعة نشطة",
        "order": 4,
    },
    "avoid_defer": {
        "en": "Avoid / Defer",
        "ar": "تجنب / تأجيل",
        "order": 5,
    },
}

# Rule stubs only — NO numeric suitability→action auto-assignment
REGENERATION_RULE_STUBS = [
    {
        "id": "stub_protect",
        "ladder": "protect_natural_regeneration",
        "rule_stub_en": (
            "When field evidence shows intact natural recruits and low disturbance pressure, "
            "prefer protection over planting. Auto-assign from satellite suitability is FORBIDDEN."
        ),
        "requires_field_validation": True,
        "auto_assign_from_suitability": False,
    },
    {
        "id": "stub_assisted",
        "ladder": "assisted_natural_regeneration",
        "rule_stub_en": (
            "When recruits exist but face barriers (grazing, compaction), assist regeneration. "
            "Manual expert choice only in Phase 2 — no numeric score→action wiring."
        ),
        "requires_field_validation": True,
        "auto_assign_from_suitability": False,
    },
    {
        "id": "stub_enrichment",
        "ladder": "enrichment_seeding",
        "rule_stub_en": (
            "Enrichment seeding stub — Authority-vetted fog-escarpment list only; "
            "never mix Najd arid species onto escarpment recommendations."
        ),
        "requires_field_validation": True,
        "auto_assign_from_suitability": False,
    },
    {
        "id": "stub_active",
        "ladder": "active_planting",
        "rule_stub_en": (
            "Active planting stub — campaign hectares / seed kg / crew days FORBIDDEN "
            "as official numbers until field validation."
        ),
        "requires_field_validation": True,
        "auto_assign_from_suitability": False,
    },
    {
        "id": "stub_avoid",
        "ladder": "avoid_defer",
        "rule_stub_en": (
            "Avoid / defer when evidence is insufficient, slope/hazard unsafe, or science lock applies."
        ),
        "requires_field_validation": True,
        "auto_assign_from_suitability": False,
    },
]


def regeneration_ladder_doc() -> dict[str, Any]:
    return {
        "schema_ref": "docs/spec_0.4/natural_regeneration_ladder.schema.json",
        "science_lock": "SCIENCE_LOCKS_v0.4_phase1_2.md §6",
        "status": "enum_and_rule_stubs_only",
        "provisional": True,
        "auto_assign_from_suitability": False,
        "forbidden": [
            "numeric_suitability_to_action_auto_assignment",
            "campaign_hectares_as_official",
            "seed_kg_as_official",
            "crew_days_as_official",
            "species_suitability_scores_as_operational_truth",
        ],
        "ladder_enum": REGENERATION_LADDER_ENUM,
        "labels": REGENERATION_LADDER_LABELS,
        "rule_stubs": REGENERATION_RULE_STUBS,
        "note_en": (
            "Phase-2 coding: enum + rule stubs OK. Numeric suitability→action auto-assignment "
            "to partners requires field validation (Forbidden table)."
        ),
    }
