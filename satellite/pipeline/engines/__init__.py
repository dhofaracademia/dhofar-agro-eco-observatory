"""v0.4 Phase-1 agricultural + Phase-3 decision + Phase-4 seed + Phase-5 field engines.

Formulas locked by docs/SCIENCE_LOCKS_v0.4_phase1_2.md (Agrofostery).
Phase-4 species: docs/SCIENCE_LOCKS_v0.4_phase4_species.md
Phase-5 field: docs/SCIENCE_LOCKS_v0.4_phase5_field_loop.md

Do not invent alternate equations or auto-rewrite scores without Agrofostery sign-off.
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
from .suitability import compute_suitability, WEIGHTS_NOMINAL as SUITABILITY_WEIGHTS
from .confidence import compute_confidence, WEIGHTS_NOMINAL as CONFIDENCE_WEIGHTS
from .evidence_gap import assess_evidence_gaps
from .seed_intelligence import (
    build_catalog,
    load_scaffold_species,
    normalize_domain,
    timing_for_domain,
)
from .field_loop import (
    create_planned_followups,
    validate_seeding_event,
    germination_not_applicable,
    build_field_loop_wrapper,
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
    "compute_suitability",
    "SUITABILITY_WEIGHTS",
    "compute_confidence",
    "CONFIDENCE_WEIGHTS",
    "assess_evidence_gaps",
    "build_catalog",
    "load_scaffold_species",
    "normalize_domain",
    "timing_for_domain",
    "create_planned_followups",
    "validate_seeding_event",
    "germination_not_applicable",
    "build_field_loop_wrapper",
]
