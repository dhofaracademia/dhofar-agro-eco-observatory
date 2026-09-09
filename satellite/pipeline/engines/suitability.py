"""Agriculture AOU Suitability — Phase-3 Decision Engine (Agrofostery locks).

Suitability domain: agriculture_aou
Status: expert_v1_provisional

Weights (renorm if missing):
  agricultural_probability/100 × 0.35
  NDVI persistence           × 0.20
  (100−vigor_stress)/100     × 0.20
  (100−water_stress)/100     × 0.15
  geometry stability         × 0.10
    (IoU≥0.3 OR area_ha≥2 → 1.0; else scaled)

AgriTech component shape (display):
  moisture_proxy, vigor_proxy, phenology_fit, terrain_constraint

HARD GATES:
  Suitability ≠ Confidence ≠ data_quality_confidence — never merge.
  mountain_apply = False — do NOT apply these weights to mountain cells.
  action_auto_assign = False — no suitability→action wiring.
  moisture/vigor = NDMI/NDVI stress proxies — NOT soil moisture %.
"""

from __future__ import annotations

from typing import Any

SUITABILITY_DOMAIN = "agriculture_aou"
STATUS = "expert_v1_provisional"
FORMULA_REF = "SCIENCE_LOCKS_v0.4_phase1_2.md§Phase3"

WEIGHTS_NOMINAL = {
    "agricultural_probability": 0.35,
    "ndvi_persistence": 0.20,
    "inverse_vigor_stress": 0.20,
    "inverse_water_stress": 0.15,
    "geometry_stability": 0.10,
}

HONESTY_EN = (
    "Provisional agriculture_aou suitability (expert_v1). "
    "Suitability ≠ Confidence ≠ data_quality_confidence — never merge. "
    "Moisture/vigor terms are NDMI/NDVI stress proxies, not plot soil moisture %. "
    "Not applied to mountain cells. No action auto-assign."
)
HONESTY_AR = (
    "ملاءمة زراعية مؤقتة لوحدات الرصد (خبير v1). "
    "الملاءمة ≠ الثقة ≠ ثقة جودة البيانات — لا تُدمَج. "
    "Proxies الرطوبة/الحيوية من NDMI/NDVI وليست رطوبة تربة %. "
    "لا تُطبَّق على خلايا الجبال. لا تعيين إجراء تلقائي."
)
NEQ_EN = "Suitability ≠ Confidence — these scores are never merged into one misleading number."
NEQ_AR = "الملاءمة ≠ الثقة — لا تُدمَج الدرجتان في رقم واحد مضلّل."


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


def geometry_stability(
    *,
    prior_iou: float | None = None,
    area_ha: float | None = None,
    iou_thr: float = 0.3,
    min_area_ha: float = 2.0,
) -> float:
    """1.0 if IoU≥0.3 or area≥2ha; else partial credit from area or IoU."""
    if prior_iou is not None and prior_iou >= iou_thr:
        return 1.0
    if area_ha is not None and area_ha >= min_area_ha:
        return 1.0
    if prior_iou is not None:
        return _clip01(prior_iou / iou_thr) or 0.0
    if area_ha is not None and area_ha > 0:
        return _clip01(area_ha / min_area_ha) or 0.0
    return 0.0


def ndvi_persistence_feature(
    *,
    n_clear_dates: int | None = None,
    persistence_score_0_1: float | None = None,
    agricultural_probability: float | None = None,
) -> float | None:
    """Prefer explicit persistence; else derive a thin provisional proxy.

    Not inventing multi-date truth: single-date → capped low persistence.
    """
    if persistence_score_0_1 is not None:
        return _clip01(persistence_score_0_1)
    if n_clear_dates is not None:
        # Cap: ≥4 clear dates → 1.0; 1 date → 0.25 (cannot claim persistence)
        if n_clear_dates <= 0:
            return 0.0
        if n_clear_dates == 1:
            return 0.25
        return _clip01(n_clear_dates / 4.0)
    if agricultural_probability is not None:
        # Last-resort weak proxy — stamped provisional via status
        return _clip01(float(agricultural_probability) / 100.0 * 0.5)
    return None


def compute_suitability(
    *,
    aou_id: str,
    agricultural_probability: float | None = None,
    water_stress_score: float | None = None,
    vigor_stress_score: float | None = None,
    ndvi_persistence: float | None = None,
    n_clear_dates: int | None = None,
    prior_iou: float | None = None,
    area_ha: float | None = None,
    observation_date: str | None = None,
    product_id: str | None = None,
    tile: str | None = None,
    source: str | None = None,
    ndre_available: bool | None = None,
    evidence_gap_codes: list[str] | None = None,
) -> dict[str, Any]:
    """Return agriculture_aou suitability record (AgriTech + Agrofostery locks)."""
    ag_norm = _clip01(None if agricultural_probability is None else agricultural_probability / 100.0)
    moisture = _clip01(None if water_stress_score is None else (100.0 - float(water_stress_score)) / 100.0)
    vigor = _clip01(None if vigor_stress_score is None else (100.0 - float(vigor_stress_score)) / 100.0)
    phenology = ndvi_persistence_feature(
        n_clear_dates=n_clear_dates,
        persistence_score_0_1=ndvi_persistence,
        agricultural_probability=agricultural_probability,
    )
    terrain = geometry_stability(prior_iou=prior_iou, area_ha=area_ha)

    present = {
        "agricultural_probability": ag_norm is not None,
        "ndvi_persistence": phenology is not None,
        "inverse_vigor_stress": vigor is not None,
        "inverse_water_stress": moisture is not None,
        "geometry_stability": True,  # always computable (defaults to 0)
    }
    w = _renorm(WEIGHTS_NOMINAL, present)

    score: float | None = None
    if any(present[k] for k in present if k != "geometry_stability") or area_ha is not None:
        score = 100.0 * (
            w["agricultural_probability"] * (ag_norm or 0.0)
            + w["ndvi_persistence"] * (phenology or 0.0)
            + w["inverse_vigor_stress"] * (vigor or 0.0)
            + w["inverse_water_stress"] * (moisture or 0.0)
            + w["geometry_stability"] * terrain
        )
        score = round(max(0.0, min(100.0, score)), 2)

    drivers = _drivers(
        aou_id=aou_id,
        ag_norm=ag_norm,
        moisture=moisture,
        vigor=vigor,
        phenology=phenology,
        terrain=terrain,
        score=score,
    )
    cautions = _cautions(
        ndre_available=ndre_available,
        n_clear_dates=n_clear_dates,
        prior_iou=prior_iou,
        evidence_gap_codes=evidence_gap_codes or [],
    )
    why = {
        "headline": _headline(aou_id, score, ag_norm),
        "drivers": drivers,
        "cautions": cautions,
        "recommended_next_step": _next_step(moisture, vigor, evidence_gap_codes or []),
        "action_ladder_suggestion": None,  # MANUAL ONLY — must stay null
    }

    return {
        "aou_id": aou_id,
        "suitability_domain": SUITABILITY_DOMAIN,
        "status": STATUS,
        "suitability_score": score,
        "suitability_summary_label": "components_only",
        "suitability_components": {
            "moisture_proxy": None if moisture is None else round(moisture, 4),
            "vigor_proxy": None if vigor is None else round(vigor, 4),
            "phenology_fit": None if phenology is None else round(phenology, 4),
            "terrain_constraint": round(terrain, 4),
            "agricultural_probability_norm": None if ag_norm is None else round(ag_norm, 4),
        },
        "weights_used": {k: round(v, 4) for k, v in w.items()},
        "weights_nominal": dict(WEIGHTS_NOMINAL),
        "cite_slots": {
            "formula_ref": FORMULA_REF,
            "observation_date": observation_date,
            "product_id": product_id,
            "tile": tile,
            "source": source,
        },
        "honesty_note_en": HONESTY_EN,
        "honesty_note_ar": HONESTY_AR,
        "suitability_neq_confidence_note_en": NEQ_EN,
        "suitability_neq_confidence_note_ar": NEQ_AR,
        "never_merge_with_confidence": True,
        "mountain_apply": False,
        "action_auto_assign": False,
        "why_this_site": why,
    }


def _headline(aou_id: str, score: float | None, ag_norm: float | None) -> str:
    if score is None:
        return f"{aou_id}: suitability components incomplete — provisional scaffold only"
    band = "higher" if score >= 60 else ("moderate" if score >= 40 else "lower")
    ag = f"; ag_probability_norm={ag_norm:.2f}" if ag_norm is not None else ""
    return (
        f"{aou_id}: provisional agriculture_aou suitability {score:.1f}/100 "
        f"({band} relative among components{ag}) — expert_v1_provisional, not operational truth"
    )


def _drivers(
    *,
    aou_id: str,
    ag_norm: float | None,
    moisture: float | None,
    vigor: float | None,
    phenology: float | None,
    terrain: float,
    score: float | None,
) -> list[str]:
    bullets: list[str] = []
    if ag_norm is not None:
        bullets.append(f"Agricultural probability (norm) available: {ag_norm:.2f} (weight 0.35).")
    if moisture is not None:
        bullets.append(
            f"Moisture proxy from inverse water_stress (NDMI-based): {moisture:.2f} — not soil moisture %."
        )
    if vigor is not None:
        bullets.append(
            f"Vigor proxy from inverse vigor_stress (NDVI-based): {vigor:.2f} — not fertilizer diagnosis."
        )
    if phenology is not None:
        bullets.append(f"Phenology / NDVI persistence fit: {phenology:.2f}.")
    bullets.append(f"Geometry stability (AOU IoU/area gate): {terrain:.2f}.")
    if score is not None:
        bullets.append(
            f"Weighted suitability_score={score:.1f} shown as components_only "
            f"(Suitability ≠ Confidence)."
        )
    if not any([ag_norm, moisture, vigor, phenology]):
        bullets.append(f"{aou_id}: few scored inputs — evidence bullets limited to available fields.")
    return bullets


def _cautions(
    *,
    ndre_available: bool | None,
    n_clear_dates: int | None,
    prior_iou: float | None,
    evidence_gap_codes: list[str],
) -> list[str]:
    out = [
        "expert_v1_provisional — Agrofostery weight locks; not field-validated operational truth.",
        "Do not merge with Confidence or data_quality_confidence.",
        "Mountain cells: mountain_apply=false — these weights must not be used.",
        "action_ladder_suggestion remains null (manual enum only).",
    ]
    if ndre_available is False:
        out.append("NDRE unavailable on this AOU observation.")
    if n_clear_dates is not None and n_clear_dates <= 1:
        out.append("Thin AOU clear-date history — persistence is a weak provisional proxy.")
    if prior_iou is None:
        out.append("No prior IoU (new or unmatched ID) — geometry stability uses area gate only.")
    for code in evidence_gap_codes:
        out.append(f"Evidence gap: {code}")
    return out


def _next_step(
    moisture: float | None,
    vigor: float | None,
    gap_codes: list[str],
) -> str:
    """Manual recommended next step text only — never an action enum auto-assign."""
    _ = gap_codes  # gaps inform cautions; ladder suggestion stays null upstream
    if moisture is not None and moisture < 0.45:
        return (
            "Manual next step: field irrigation inspection recommended "
            "(provisional — not auto-assigned from suitability)."
        )
    if vigor is not None and vigor < 0.45:
        return (
            "Manual next step: field vigor inspection recommended "
            "(provisional — not auto-assigned from suitability)."
        )
    return (
        "Manual next step: continue monitoring and schedule field verification "
        "when evidence gaps shrink — action ladder remains manual."
    )
