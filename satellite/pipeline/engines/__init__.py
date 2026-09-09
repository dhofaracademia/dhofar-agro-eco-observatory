"""v0.4 Phase-1 agricultural engines.

Formulas locked by docs/SCIENCE_LOCKS_v0.4_phase1_2.md (Agrofostery).
Do not invent alternate AgProb / Stress / Biotic / NDRE equations without
Agrofostery sign-off.
"""

from .ndre import compute_ndre, ndre_status_from_band
from .ag_probability import (
    AG_WEIGHTS,
    ag_class_from_probability,
    agricultural_probability,
    redistribute_ndre_weight,
)
from .stress import water_stress_score, vigor_stress_score, map_stress_to_alert
from .biotic import biotic_stress_risk
from .aou_identity import (
    mint_or_match_aou,
    segment_probability_mask,
    load_registry,
    save_registry,
)

__all__ = [
    "compute_ndre",
    "ndre_status_from_band",
    "AG_WEIGHTS",
    "ag_class_from_probability",
    "agricultural_probability",
    "redistribute_ndre_weight",
    "water_stress_score",
    "vigor_stress_score",
    "map_stress_to_alert",
    "biotic_stress_risk",
    "mint_or_match_aou",
    "segment_probability_mask",
    "load_registry",
    "save_registry",
]
