"""Seed Intelligence scaffold — SCIENCE_LOCKS_v0.4_phase4_species.

Domains (never mix): fog_escarpment | najd_arid
vetting_status: scientist_locked_pending_ea (NOT Authority-approved)
Scores: unvalidated / null — no campaign numbers — mountain UI Hold
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIR.parents[1]
SCAFFOLD_PATH = REPO_ROOT / "docs" / "phase4_species_scaffold.json"
OUT_DIR = PIPELINE_DIR / "artifacts" / "seed"

ECOLOGICAL_DOMAINS = ("fog_escarpment", "najd_arid")
# Former internal aliases — not ecological domain ids
DOMAIN_ALIASES = {
    "agriculture_aou": "najd_arid",
    "restoration_mountain": "fog_escarpment",
}

PROVENANCE_ENUM = [
    "local_same_jabal",
    "regional_dhofar",
    "oman_other",
    "unknown",
    "blocked_exotic",
]
PROVENANCE_DEFAULT = "unknown"

DISCLAIMER_EN = (
    "Unvalidated expert stub — not an Environment Authority approval, "
    "not a field-tested score."
)
DISCLAIMER_AR = (
    "مسودة خبير غير مُتحقق منها — ليست موافقة من هيئة البيئة، "
    "وليست درجة مختبرة ميدانياً."
)

FORBIDDEN_LABELS = (
    "Authority-approved",
    "معتمد من الهيئة",
)


def load_scaffold_species() -> list[dict[str, Any]]:
    doc = json.loads(SCAFFOLD_PATH.read_text(encoding="utf-8"))
    return [s for s in doc.get("species", []) if s.get("scaffold_include")]


def normalize_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    if domain in ECOLOGICAL_DOMAINS:
        return domain
    return DOMAIN_ALIASES.get(domain)


def timing_for_domain(domain: str, *, mpi_insufficient: bool = False, t0_onset_fallback: bool = False) -> str | None:
    if domain == "fog_escarpment":
        if mpi_insufficient or t0_onset_fallback:
            return "deferred"
        return None  # assign late_khareef | early_post_khareef only when clear post-khareef exists
    if domain == "najd_arid":
        return None  # winter_spring_rain | irrigated — never mountain MPI
    return None


def build_catalog() -> dict[str, Any]:
    species = load_scaffold_species()
    if len(species) != 6:
        raise ValueError(f"expected 6 scaffold species, got {len(species)}")
    rows = []
    for s in species:
        domain = s["domain"]
        if domain not in ECOLOGICAL_DOMAINS:
            raise ValueError(f"invalid domain {domain}")
        rows.append(
            {
                "species_id": s["species_id"],
                "domain": domain,
                "ecological_domain": domain,
                "accepted_name": s["accepted_name"],
                "species_name_sci": s["accepted_name"],
                "ar_name": s["ar_name"],
                "ar_name_alt": s.get("ar_name_alt", []),
                "en_name": s.get("en_name"),
                "establishment_mode": s.get("establishment_mode"),
                "timing_window": s.get("timing_window"),
                "vetting_status": "scientist_locked_pending_ea",
                "score_status": "unvalidated",
                "suitability_provisional_0_100": None,
                "status": "unvalidated_expert_stub",
            }
        )
    return {
        "version": "phase4_scientist_lock_v1",
        "vetting_status": "scientist_locked_pending_ea",
        "score_status": "unvalidated",
        "science_lock": "SCIENCE_LOCKS_v0.4_phase4_species",
        "product_spec_cite": "1.0.1 §12",
        "domains": list(ECOLOGICAL_DOMAINS),
        "never_mix_domains": True,
        "mountain_ui": "hold",
        "campaign_numbers": False,
        "provenance_enum": PROVENANCE_ENUM,
        "provenance_default": PROVENANCE_DEFAULT,
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
        "forbidden_labels": list(FORBIDDEN_LABELS),
        "species": rows,
    }
