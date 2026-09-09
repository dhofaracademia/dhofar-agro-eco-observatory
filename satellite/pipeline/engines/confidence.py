"""Data-evidence Confidence — Phase-3 Decision Engine (Agrofostery locks).

Confidence domain: data_evidence
Status: expert_v1_provisional

Weights (renorm if missing):
  data_quality_confidence/100 × 0.40
  n_clear_dates/8 (cap 1)     × 0.25
  historical depth            × 0.20
    (0 / 0.5 / 1 for 0 / 1 / 2+ prior seasons)
  prior IoU (0 if new ID)     × 0.15

AgriTech fields:
  data_quality_confidence, temporal_coverage_confidence,
  spatial_clarity_confidence, overall_confidence

HARD GATES:
  Confidence ≠ Suitability ≠ data_quality_confidence alone.
  Not ecological certainty.
  mountain_apply = False.
"""

from __future__ import annotations

from typing import Any

CONFIDENCE_DOMAIN = "data_evidence"
STATUS = "expert_v1_provisional"
FORMULA_REF = "SCIENCE_LOCKS_v0.4_phase1_2.md§Phase3"

WEIGHTS_NOMINAL = {
    "data_quality": 0.40,
    "n_clear_dates": 0.25,
    "historical_depth": 0.20,
    "prior_iou": 0.15,
}

HONESTY_EN = (
    "Provisional data_evidence confidence (expert_v1). "
    "Not ecological certainty. "
    "Suitability ≠ Confidence ≠ data_quality_confidence alone — never merge. "
    "Not applied to mountain cells."
)
HONESTY_AR = (
    "ثقة أدلة البيانات مؤقتة (خبير v1). "
    "ليست يقيناً بيئياً. "
    "الملاءمة ≠ الثقة ≠ ثقة جودة البيانات وحدها — لا تُدمَج. "
    "لا تُطبَّق على خلايا الجبال."
)


def _clip01(x: float | None) -> float | None:
    if x is None:
        return None
    return max(0.0, min(1.0, float(x)))


def _renorm(weights: dict[str, float], present: dict[str, bool]) -> dict[str, float]:
    active = {k: v for k, v in weights.items() if present.get(k, False)}
    s = sum(active.values())
    if s <= 0:
        return {k: 0.0 for k in weights}
    return {k: (active[k] / s if k in active else 0.0) for k in weights}


def historical_depth_term(prior_seasons_count: int | None) -> float | None:
    """0 / 0.5 / 1 for 0 / 1 / 2+ prior seasons."""
    if prior_seasons_count is None:
        return None
    n = max(0, int(prior_seasons_count))
    if n <= 0:
        return 0.0
    if n == 1:
        return 0.5
    return 1.0


def compute_confidence(
    *,
    aou_id: str,
    data_quality_confidence: float | None = None,
    n_clear_dates: int | None = None,
    prior_seasons_count: int | None = None,
    prior_iou: float | None = None,
    is_new_id: bool | None = None,
    observation_date: str | None = None,
    product_id: str | None = None,
) -> dict[str, Any]:
    """Return data_evidence confidence record."""
    new_id = bool(is_new_id) if is_new_id is not None else (prior_iou is None)
    dq_norm = _clip01(None if data_quality_confidence is None else float(data_quality_confidence) / 100.0)
    n_clear = None if n_clear_dates is None else max(0, int(n_clear_dates))
    n_clear_norm = None if n_clear is None else _clip01(n_clear / 8.0)
    hist = historical_depth_term(prior_seasons_count)
    # If seasons unknown but only 1 observation date → treat as 0 seasons depth
    if hist is None and n_clear is not None and n_clear <= 1:
        hist = 0.0
    iou = 0.0 if new_id else (_clip01(prior_iou) if prior_iou is not None else 0.0)

    present = {
        "data_quality": dq_norm is not None,
        "n_clear_dates": n_clear_norm is not None,
        "historical_depth": hist is not None,
        "prior_iou": True,  # 0 if new ID — always present as a term
    }
    w = _renorm(WEIGHTS_NOMINAL, present)

    overall: float | None = None
    if dq_norm is not None or n_clear_norm is not None or hist is not None:
        overall = 100.0 * (
            w["data_quality"] * (dq_norm or 0.0)
            + w["n_clear_dates"] * (n_clear_norm or 0.0)
            + w["historical_depth"] * (hist or 0.0)
            + w["prior_iou"] * (iou or 0.0)
        )
        overall = round(max(0.0, min(100.0, overall)), 2)

    temporal_cov = None if n_clear_norm is None else round(n_clear_norm * 100.0, 2)
    spatial_clarity = round((iou or 0.0) * 100.0, 2)

    return {
        "aou_id": aou_id,
        "confidence_domain": CONFIDENCE_DOMAIN,
        "status": STATUS,
        "data_quality_confidence": (
            None if data_quality_confidence is None else round(float(data_quality_confidence), 2)
        ),
        "temporal_coverage_confidence": temporal_cov,
        "spatial_clarity_confidence": spatial_clarity,
        "overall_confidence": overall,
        "components": {
            "data_quality_norm": None if dq_norm is None else round(dq_norm, 4),
            "n_clear_dates_norm": None if n_clear_norm is None else round(n_clear_norm, 4),
            "historical_depth": hist,
            "prior_iou": round(iou or 0.0, 4),
        },
        "weights_used": {k: round(v, 4) for k, v in w.items()},
        "weights_nominal": dict(WEIGHTS_NOMINAL),
        "n_clear_dates": n_clear,
        "prior_seasons_count": prior_seasons_count,
        "is_new_id": new_id,
        "cite_slots": {
            "formula_ref": FORMULA_REF,
            "observation_date": observation_date,
            "product_id": product_id,
        },
        "honesty_note_en": HONESTY_EN,
        "honesty_note_ar": HONESTY_AR,
        "never_merge_with_suitability": True,
        "not_ecological_certainty": True,
        "mountain_apply": False,
    }
