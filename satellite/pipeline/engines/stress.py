"""Water / Vigor Stress Scores — SCIENCE_LOCKS §3 (binding).

W = 0.40*relative + 0.25*historical + 0.25*persistence + 0.10*phenology_penalty
Missing historical → renormalize remaining weights.
Same structure for Vigor on NDVI (and NDRE if present).
Map high W → water_attention; high V → vigor_attention.
"""

from __future__ import annotations

from typing import Any

W_REL, W_HIST, W_PERS, W_PHEN = 0.40, 0.25, 0.25, 0.10
# Attention thresholds (0–100 score); expert defaults pending field calibration
WATER_ATTENTION_THR = 55.0
VIGOR_ATTENTION_THR = 55.0


def _renorm(weights: dict[str, float], present: dict[str, bool]) -> dict[str, float]:
    active = {k: v for k, v in weights.items() if present.get(k, False)}
    s = sum(active.values())
    if s <= 0:
        return {k: 0.0 for k in weights}
    return {k: (active[k] / s if k in active else 0.0) for k in weights}


def _clip100(x: float) -> float:
    return max(0.0, min(100.0, float(x)))


def relative_anomaly_score(value: float, peer_p25: float, peer_p50: float | None = None) -> float:
    """Higher = more stress. Value below peer p25 → elevated."""
    if value is None or peer_p25 is None:
        return 50.0
    # Distance below p25 scaled; at/above p50 → low stress
    ref_hi = peer_p50 if peer_p50 is not None else peer_p25 + 0.05
    if value >= ref_hi:
        return 10.0
    if value >= peer_p25:
        # between p25 and p50
        span = max(ref_hi - peer_p25, 1e-6)
        return _clip100(40.0 * (1.0 - (value - peer_p25) / span))
    # below p25
    span = max(abs(peer_p25) * 0.5 + 0.05, 0.05)
    return _clip100(55.0 + 45.0 * min(1.0, (peer_p25 - value) / span))


def historical_anomaly_score(value: float | None, hist_median: float | None) -> float | None:
    if value is None or hist_median is None:
        return None
    if value >= hist_median:
        return 15.0
    span = max(abs(hist_median) * 0.4 + 0.03, 0.03)
    return _clip100(50.0 + 50.0 * min(1.0, (hist_median - value) / span))


def persistence_score(flags_last_n: list[bool]) -> float:
    """Stress flag true on ≥2 of last 3 clear observations → high."""
    if not flags_last_n:
        return 40.0  # unknown → mild neutral
    n = len(flags_last_n)
    hits = sum(1 for f in flags_last_n if f)
    if n >= 3 and hits >= 2:
        return 90.0
    if hits >= 1:
        return 55.0
    return 15.0


def phenology_penalty_water(month: int | None, ndvi: float | None) -> float:
    """Down-weight water stress in expected senescence / post-harvest (Apr–May Najd)."""
    if month in (4, 5) and (ndvi is None or ndvi < 0.25):
        return 15.0  # low penalty contribution toward stress (expected bare rebound)
    if month in (4, 5):
        return 35.0
    return 50.0  # neutral phenology term (not reducing stress claim)


def phenology_penalty_vigor(month: int | None, ndvi: float | None) -> float:
    if month in (4, 5) and (ndvi is None or ndvi < 0.22):
        return 20.0
    return 50.0


def _combine(
    relative: float,
    historical: float | None,
    persistence: float,
    phenology: float,
) -> tuple[float, dict[str, float]]:
    base = {
        "relative": W_REL,
        "historical": W_HIST,
        "persistence": W_PERS,
        "phenology": W_PHEN,
    }
    present = {
        "relative": True,
        "historical": historical is not None,
        "persistence": True,
        "phenology": True,
    }
    w = _renorm(base, present)
    hist_v = historical if historical is not None else 0.0
    score = (
        w["relative"] * relative
        + w["historical"] * hist_v
        + w["persistence"] * persistence
        + w["phenology"] * phenology
    )
    return round(_clip100(score), 2), {k: round(v, 4) for k, v in w.items()}


def water_stress_score(
    *,
    ndmi: float,
    ndmi_p25_veg: float,
    ndmi_p50_veg: float | None = None,
    ndmi_hist_median: float | None = None,
    stress_flags_recent: list[bool] | None = None,
    month: int | None = None,
    ndvi: float | None = None,
) -> dict[str, Any]:
    rel = relative_anomaly_score(ndmi, ndmi_p25_veg, ndmi_p50_veg)
    hist = historical_anomaly_score(ndmi, ndmi_hist_median)
    pers = persistence_score(stress_flags_recent or [])
    phen = phenology_penalty_water(month, ndvi)
    score, weights = _combine(rel, hist, pers, phen)
    return {
        "water_stress_score": score,
        "components": {
            "relative": round(rel, 2),
            "historical": None if hist is None else round(hist, 2),
            "persistence": round(pers, 2),
            "phenology": round(phen, 2),
        },
        "weights_used": weights,
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§3.1",
        "status": "expert_v1",
    }


def vigor_stress_score(
    *,
    ndvi: float,
    ndvi_p25_veg: float,
    ndvi_p50_veg: float | None = None,
    ndvi_hist_median: float | None = None,
    ndre: float | None = None,
    ndre_p25: float | None = None,
    stress_flags_recent: list[bool] | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    # Prefer NDVI; if NDRE present, blend 70/30 into relative term
    rel_ndvi = relative_anomaly_score(ndvi, ndvi_p25_veg, ndvi_p50_veg)
    if ndre is not None and ndre_p25 is not None:
        rel_ndre = relative_anomaly_score(ndre, ndre_p25, None)
        rel = 0.7 * rel_ndvi + 0.3 * rel_ndre
    else:
        rel = rel_ndvi
    hist = historical_anomaly_score(ndvi, ndvi_hist_median)
    pers = persistence_score(stress_flags_recent or [])
    phen = phenology_penalty_vigor(month, ndvi)
    score, weights = _combine(rel, hist, pers, phen)
    return {
        "vigor_stress_score": score,
        "components": {
            "relative": round(rel, 2),
            "historical": None if hist is None else round(hist, 2),
            "persistence": round(pers, 2),
            "phenology": round(phen, 2),
        },
        "weights_used": weights,
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§3.2",
        "status": "expert_v1",
        "note": "High vigor stress → management / possible nutrient — NOT fertilizer diagnosis",
    }


def map_stress_to_alert(
    *,
    ndvi: float,
    bare_floor: float,
    water: dict[str, Any],
    vigor: dict[str, Any],
    data_quality_confidence: float,
    unclear_dq_thr: float = 35.0,
) -> str:
    """Map scores to existing four UI codes (+ bare/unclear)."""
    if data_quality_confidence < unclear_dq_thr:
        return "unclear"
    if ndvi < bare_floor:
        return "bare"
    w = water.get("water_stress_score", 0)
    v = vigor.get("vigor_stress_score", 0)
    if w >= WATER_ATTENTION_THR and w >= v:
        return "water_attention"
    if v >= VIGOR_ATTENTION_THR:
        return "vigor_attention"
    return "healthy"
