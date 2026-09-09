"""Biotic Stress Risk — SCIENCE_LOCKS §4.

ONLY label: possible_biotic_stress.
FORBIDDEN: pest name, disease name, confirmed infestation.
All four rules required for flag (spatial, temporal, persistence, DQ gate).
"""

from __future__ import annotations

from typing import Any

DISCLAIMER_EN = (
    "Possible biotic stress — satellite cannot confirm pest or disease. "
    "Field verification recommended."
)
DISCLAIMER_AR = (
    "إجهاد حيوي محتمل — القمر الصناعي لا يؤكد آفة أو مرضاً. يُوصى بالتحقق الميداني."
)


def biotic_stress_risk(
    *,
    spatial_anomaly: bool,
    temporal_faster_than_phenology: bool,
    not_explained_by_water_alone: bool,
    persistence_ok: bool,
    data_quality_ok: bool,
) -> dict[str, Any]:
    """Return risk-only structure. Never emits pest certainty."""
    rules = {
        "spatial_anomaly": bool(spatial_anomaly),
        "temporal_vs_phenology": bool(temporal_faster_than_phenology),
        "not_water_alone": bool(not_explained_by_water_alone),
        "persistence_ge_2": bool(persistence_ok),
        "data_quality_ok": bool(data_quality_ok),
    }
    flagged = all(rules.values())
    return {
        "possible_biotic_stress": flagged,
        "biotic_risk_label": "possible_biotic_stress" if flagged else None,
        "rules": rules,
        "disclaimer_en": DISCLAIMER_EN,
        "disclaimer_ar": DISCLAIMER_AR,
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§4",
        "forbidden": ["pest_name", "disease_name", "confirmed_infestation"],
    }


def infer_biotic_from_cell(
    *,
    ndvi: float,
    ndmi: float,
    ndvi_p25: float,
    ndmi_p25: float,
    vigor_stress: float,
    water_stress: float,
    neighbor_ndvi_median: float | None,
    data_quality_confidence: float,
    prior_vigor_flags: list[bool] | None = None,
) -> dict[str, Any]:
    """Heuristic Phase-1 inference from single-date + optional persistence flags.

    Spatial: NDVI distinctly below immediate peers / neighbor median (patch-like).
    Temporal: vigor high while water not dominant (NDMI OK-ish).
    Persistence (SCIENCE_LOCKS §4): ≥2 clear dates only — pass prior vigor
    flags and/or flags_last_n including current; persistence_ok when ≥2 True
    entries. Single-date (and the former soft path of 1 prior + strong current)
    cannot clear persistence alone.
    """
    neighbor = neighbor_ndvi_median if neighbor_ndvi_median is not None else ndvi_p25
    spatial = ndvi < (neighbor - 0.05) and ndvi < ndvi_p25
    water_ok = ndmi >= ndmi_p25 or water_stress < 50
    temporal = vigor_stress >= 60 and water_ok
    not_water = water_stress < vigor_stress and water_ok
    # flags_last_n may include current; require ≥2 True dates (no soft path)
    flags = prior_vigor_flags or []
    persistence = sum(1 for f in flags if f) >= 2
    dq = data_quality_confidence >= 40
    return biotic_stress_risk(
        spatial_anomaly=spatial,
        temporal_faster_than_phenology=temporal,
        not_explained_by_water_alone=not_water,
        persistence_ok=persistence,
        data_quality_ok=dq,
    )
