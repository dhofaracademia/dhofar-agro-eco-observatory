"""Agricultural Probability Engine — SCIENCE_LOCKS §1 (binding).

Core weights (sum 1.0 when NDRE present):
  NDVI peak 0.22, persistence 0.18, NDMI 0.15, SWIR 0.12,
  NDRE 0.10, phenology 0.13, texture 0.10.
If NDRE unavailable → redistribute 0.10 to NDVI peak + NDMI (half each).
S1/DW are assists only (not implemented as sole voters in Phase 1).
Gates: SCL already applied; <3 clear → max class possible;
single-date spike alone cannot reach very_likely.
"""

from __future__ import annotations

from typing import Any

AG_WEIGHTS = {
    "ndvi_peak": 0.22,
    "persistence": 0.18,
    "ndmi": 0.15,
    "swir": 0.12,
    "ndre": 0.10,
    "phenology": 0.13,
    "texture": 0.10,
}

AG_CLASS_BREAKS = (
    (30, "unlikely"),
    (60, "possible"),
    (80, "likely"),
    (101, "very_likely"),
)


def redistribute_ndre_weight(ndre_available: bool) -> dict[str, float]:
    w = dict(AG_WEIGHTS)
    if ndre_available:
        return w
    # SCIENCE_LOCKS / AgriTech: omit NDRE, renorm 0.10 → NDVI+NDMI
    extra = w.pop("ndre")
    w["ndvi_peak"] = round(w["ndvi_peak"] + extra / 2.0, 6)
    w["ndmi"] = round(w["ndmi"] + extra / 2.0, 6)
    return w


def ag_class_from_probability(
    prob_0_100: float,
    *,
    n_clear_dates: int = 1,
    persistence_feature: float = 0.0,
    single_date_only: bool = False,
) -> str:
    p = max(0.0, min(100.0, float(prob_0_100)))
    label = "unlikely"
    for hi, name in AG_CLASS_BREAKS:
        if p < hi:
            label = name
            break
    # Gate: <3 clear → cap at possible
    if n_clear_dates < 3 and label in ("likely", "very_likely"):
        label = "possible"
    # Gate: single-date NDVI spike alone cannot reach very_likely
    if (single_date_only or n_clear_dates < 2) and label == "very_likely":
        label = "likely"
    if persistence_feature < 0.15 and label == "very_likely":
        label = "likely"
    return label


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def feature_ndvi_peak(ndvi: float, bare_floor: float = 0.18) -> float:
    """Map NDVI above bare floor into 0–1 seasonal peak proxy."""
    if ndvi is None:
        return 0.0
    return _clip01((float(ndvi) - bare_floor) / (0.75 - bare_floor))


def feature_ndmi(ndmi: float, bare_ndmi: float = -0.05) -> float:
    if ndmi is None:
        return 0.0
    return _clip01((float(ndmi) - bare_ndmi) / (0.35 - bare_ndmi))


def feature_swir_response(ndvi: float, ndmi: float) -> float:
    """Low SWIR with high NDVI proxy: use NDMI contrast when B11/B12 not separate.

    When only NDVI/NDMI available (offline enrichment), approximate crop-vs-soil
    SWIR response as moist vegetated contrast. Full STAC path may pass
    explicit swir_feature from B11/B12 brightness.
    """
    if ndvi is None or ndmi is None:
        return 0.0
    # High NDVI + non-bright-dry SWIR (higher NDMI) → higher score
    return _clip01(0.5 * feature_ndvi_peak(ndvi) + 0.5 * feature_ndmi(ndmi))


def feature_swir_from_bands(
    b11_mean: float | None,
    b12_mean: float | None = None,
    *,
    scale: float = 10000.0,
) -> float | None:
    """Prefer explicit B11/B12 reflectance brightness → 0–1 AgProb swir feature.

    Lower mid-IR brightness with valid reflectance → higher crop/soil contrast score.
    Returns None if no SWIR band means (caller falls back to NDVI+NDMI proxy).
    """
    vals = []
    for v in (b11_mean, b12_mean):
        if v is None:
            continue
        # accept either DN (0–10000) or already-scaled reflectance
        rf = float(v) / scale if float(v) > 1.5 else float(v)
        if rf <= 0:
            continue
        vals.append(rf)
    if not vals:
        return None
    # Typical dry soil SWIR ~0.25–0.45; vegetated/moist lower ~0.08–0.22
    bright = sum(vals) / len(vals)
    # Invert brightness into crop-like score
    return max(0.0, min(1.0, (0.40 - bright) / 0.32))


def feature_ndre(ndre: float | None) -> float:
    if ndre is None:
        return 0.0
    return _clip01((float(ndre) - 0.05) / 0.45)


def feature_persistence(
    n_dates_above_bare: int,
    n_clear: int,
    *,
    min_dates: int = 2,
) -> float:
    if n_clear <= 0:
        return 0.0
    frac = n_dates_above_bare / max(n_clear, 1)
    if n_dates_above_bare < min_dates:
        return _clip01(frac * 0.5)
    return _clip01(frac)


def feature_phenology_proxy(ndvi: float, month: int | None) -> float:
    """Two acceptable patterns (wheat Nov–Apr peak or year-round fodder).

    Offline / single-date: soft prior — vegetated cells in wheat months score
    higher; summer green still allowed (fodder) but slightly lower.
    """
    base = feature_ndvi_peak(ndvi)
    if month is None:
        return base * 0.7
    if month in (11, 12, 1, 2, 3, 4):
        return base
    # May–Oct: fodder / residual irrigation pattern still acceptable
    return base * 0.75


def feature_texture(local_variance: float | None) -> float:
    """Edge of pivots/blocks — higher local NDVI variance → structure."""
    if local_variance is None:
        return 0.35  # neutral when unknown (grid enrichment)
    # Typical vegetated farm edge variance ~0.002–0.02 on NDVI
    return _clip01(float(local_variance) / 0.015)


def agricultural_probability(
    *,
    ndvi: float,
    ndmi: float,
    ndre: float | None = None,
    ndre_available: bool = False,
    n_clear_dates: int = 1,
    n_dates_above_bare: int = 1,
    month: int | None = None,
    local_variance: float | None = None,
    swir_feature: float | None = None,
    bare_floor: float = 0.18,
    s1_boost: float = 0.0,
    dw_veto: bool = False,
) -> dict[str, Any]:
    """Return probability 0–100 plus class and feature breakdown.

    Cite: docs/SCIENCE_LOCKS_v0.4_phase1_2.md §1.
    """
    if dw_veto:
        return {
            "agricultural_probability": 0.0,
            "ag_class": "unlikely",
            "weights": redistribute_ndre_weight(False),
            "features": {},
            "ndre_available": False,
            "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§1",
            "note": "Dynamic World veto (water/built) — assist only, no optical support",
        }

    weights = redistribute_ndre_weight(ndre_available and ndre is not None)
    feats = {
        "ndvi_peak": feature_ndvi_peak(ndvi, bare_floor),
        "persistence": feature_persistence(n_dates_above_bare, n_clear_dates),
        "ndmi": feature_ndmi(ndmi),
        "swir": swir_feature if swir_feature is not None else feature_swir_response(ndvi, ndmi),
        "phenology": feature_phenology_proxy(ndvi, month),
        "texture": feature_texture(local_variance),
    }
    if "ndre" in weights:
        feats["ndre"] = feature_ndre(ndre)

    score01 = 0.0
    for k, w in weights.items():
        score01 += w * feats.get(k, 0.0)
    # S1 assist: +0–5 points only
    boost = max(0.0, min(5.0, float(s1_boost)))
    prob = max(0.0, min(100.0, score01 * 100.0 + boost))

    single_date_only = n_clear_dates < 2
    ag_class = ag_class_from_probability(
        prob,
        n_clear_dates=n_clear_dates,
        persistence_feature=feats["persistence"],
        single_date_only=single_date_only,
    )

    return {
        "agricultural_probability": round(prob, 2),
        "ag_class": ag_class,
        "weights": weights,
        "features": {k: round(v, 4) for k, v in feats.items()},
        "ndre_available": bool(ndre_available and ndre is not None),
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§1",
        "s1_boost_pts": boost,
    }
