"""Phase-4 Seed Intelligence scaffolds — Site × Species matrix (offline).

Domains NEVER mixed:
  - agriculture_aou  → Najd AOUs (سدر / سمر / غاف + irrigated-fodder placeholders)
  - restoration_mountain → fog-escarpment (*Terminalia dhofarica* / syn. *Anogeissus dhofarica*)

HARD GATES (SCIENCE_LOCKS §Phase4 + Forbidden table):
  - status = unvalidated_expert_stub (matrix scaffold only — NOT operational truth)
  - suitability_provisional_0_100 may be null
  - Suitability ≠ Confidence
  - No campaign_ha / seed_kg / crew_days as official numbers
  - No auto campaign planner
  - No mountain partner UI / no link of mountain Decision → species candidates in UI
  - seed_recommendation + seeding_protocol = manual / operator-confirmed only
  - authority_source = pending_agrofostery until Authority list lands
  - No pest certainty; no soil moisture %; no live Khareef onset
"""

from __future__ import annotations

from typing import Any

DOMAIN_AGRICULTURE = "agriculture_aou"
DOMAIN_MOUNTAIN = "restoration_mountain"

STATUS_UNVALIDATED = "unvalidated_expert_stub"
AUTHORITY_SOURCE = "pending_agrofostery"
SCIENCE_LOCK = "SCIENCE_LOCKS_v0.4_phase1_2.md§Phase4"

FORBIDDEN = [
    "campaign_ha",
    "seed_kg",
    "crew_days",
    "operational_truth",
    "pest_certainty",
    "soil_moisture_percent",
    "live_khareef_onset",
    "cross_domain_recommend",
    "auto_campaign_planner",
]

PROTOCOL_STEPS = [
    "authority_contact",
    "site_field_check",
    "species_confirm",
    "provenance_confirm",
    "timing_confirm",
    "protocol_confirm",
    "operator_signoff",
    "defer_insufficient_evidence",
]

PROTOCOL_LABELS = {
    "authority_contact": {
        "en": "Contact Agrofostery Authority before any campaign",
        "ar": "التواصل مع سلطة الحراجة الزراعية قبل أي حملة",
        "order": 1,
    },
    "site_field_check": {
        "en": "Field-check the site",
        "ar": "معاينة ميدانية للموقع",
        "order": 2,
    },
    "species_confirm": {
        "en": "Confirm species within domain short list",
        "ar": "تأكيد النوع ضمن القائمة القصيرة للمجال",
        "order": 3,
    },
    "provenance_confirm": {
        "en": "Confirm local-preferred seed provenance",
        "ar": "تأكيد مصدر البذور المفضل محلياً",
        "order": 4,
    },
    "timing_confirm": {
        "en": "Confirm timing window (calendar heuristic only)",
        "ar": "تأكيد نافذة التوقيت (تقويم إرشادي فقط)",
        "order": 5,
    },
    "protocol_confirm": {
        "en": "Confirm seeding protocol steps",
        "ar": "تأكيد خطوات بروتوكول البذر",
        "order": 6,
    },
    "operator_signoff": {
        "en": "Operator sign-off (manual)",
        "ar": "اعتماد المشغّل (يدوي)",
        "order": 7,
    },
    "defer_insufficient_evidence": {
        "en": "Defer — insufficient evidence",
        "ar": "تأجيل — أدلة غير كافية",
        "order": 8,
    },
}


def build_species_catalog() -> dict[str, Any]:
    """Authority-pending short lists — starter rows marked unvalidated."""
    species = [
        {
            "species_id": "ziziphus_spina_christi",
            "species_name_sci": "Ziziphus spina-christi",
            "species_name_syn": None,
            "species_name_ar": "سدر",
            "species_name_en": "Christ's thorn jujube",
            "domain": DOMAIN_AGRICULTURE,
            "role": "najd_native_tree",
            "status": STATUS_UNVALIDATED,
            "local_preferred": True,
            "seed_provenance_note_en": "Local provenance preferred when available; Authority confirmation pending.",
            "seed_provenance_note_ar": "يُفضَّل المصدر المحلي عند التوفر؛ تأكيد السلطة معلّق.",
            "habitat_notes_en": "Najd arid / agriculture_aou corridor only — never fog-escarpment.",
            "habitat_notes_ar": "ممر نجد الجاف / agriculture_aou فقط — ليس منحدر الضباب.",
            "authority_source": AUTHORITY_SOURCE,
            "cross_domain_recommend": False,
        },
        {
            "species_id": "vachellia_tortilis",
            "species_name_sci": "Vachellia tortilis",
            "species_name_syn": "Acacia tortilis",
            "species_name_ar": "سمر",
            "species_name_en": "Umbrella thorn",
            "domain": DOMAIN_AGRICULTURE,
            "role": "najd_native_tree",
            "status": STATUS_UNVALIDATED,
            "local_preferred": True,
            "seed_provenance_note_en": "Local provenance preferred when available; Authority confirmation pending.",
            "seed_provenance_note_ar": "يُفضَّل المصدر المحلي عند التوفر؛ تأكيد السلطة معلّق.",
            "habitat_notes_en": "Najd arid / agriculture_aou corridor only — never fog-escarpment.",
            "habitat_notes_ar": "ممر نجد الجاف / agriculture_aou فقط — ليس منحدر الضباب.",
            "authority_source": AUTHORITY_SOURCE,
            "cross_domain_recommend": False,
        },
        {
            "species_id": "prosopis_cineraria",
            "species_name_sci": "Prosopis cineraria",
            "species_name_syn": None,
            "species_name_ar": "غاف",
            "species_name_en": "Ghaf",
            "domain": DOMAIN_AGRICULTURE,
            "role": "najd_native_tree",
            "status": STATUS_UNVALIDATED,
            "local_preferred": True,
            "seed_provenance_note_en": "Local provenance preferred when available; Authority confirmation pending.",
            "seed_provenance_note_ar": "يُفضَّل المصدر المحلي عند التوفر؛ تأكيد السلطة معلّق.",
            "habitat_notes_en": "Najd arid / agriculture_aou corridor only — never fog-escarpment.",
            "habitat_notes_ar": "ممر نجد الجاف / agriculture_aou فقط — ليس منحدر الضباب.",
            "authority_source": AUTHORITY_SOURCE,
            "cross_domain_recommend": False,
        },
        {
            "species_id": "irrigated_fodder_placeholder",
            "species_name_sci": "irrigated_fodder_placeholder",
            "species_name_syn": None,
            "species_name_ar": "أعلاف مروية (مؤقت)",
            "species_name_en": "Irrigated / fodder placeholder (unvalidated)",
            "domain": DOMAIN_AGRICULTURE,
            "role": "irrigated_fodder_placeholder",
            "status": STATUS_UNVALIDATED,
            "local_preferred": False,
            "seed_provenance_note_en": "Placeholder row only — not a species recommendation.",
            "seed_provenance_note_ar": "صف مؤقت فقط — ليس توصية نوع.",
            "habitat_notes_en": "Unvalidated irrigated/fodder slot for Najd AOUs until Authority list expands.",
            "habitat_notes_ar": "خانة أعلاف مروية غير مُتحقَّقة لوحدات نجد حتى تتوسع قائمة السلطة.",
            "authority_source": AUTHORITY_SOURCE,
            "cross_domain_recommend": False,
        },
        {
            "species_id": "terminalia_dhofarica",
            "species_name_sci": "Terminalia dhofarica",
            "species_name_syn": "Anogeissus dhofarica",
            "species_name_ar": "عتم / ترميناليا ظفارية",
            "species_name_en": "Dhofar terminalia",
            "domain": DOMAIN_MOUNTAIN,
            "role": "fog_escarpment_restoration",
            "status": STATUS_UNVALIDATED,
            "local_preferred": True,
            "seed_provenance_note_en": "Fog-escarpment only; local provenance preferred. Authority short list pending.",
            "seed_provenance_note_ar": "منحدر الضباب فقط؛ يُفضَّل المصدر المحلي. القائمة القصيرة للسلطة معلّقة.",
            "habitat_notes_en": "restoration_mountain / fog-escarpment only — never Najd arid agriculture_aou.",
            "habitat_notes_ar": "restoration_mountain / منحدر الضباب فقط — ليس نجد الجاف.",
            "authority_source": AUTHORITY_SOURCE,
            "cross_domain_recommend": False,
        },
    ]
    return {
        "version": "0.4.4-phase4-seed-scaffold",
        "status": STATUS_UNVALIDATED,
        "authority_source": AUTHORITY_SOURCE,
        "authority_contact_note_en": "Contact Agrofostery Authority before any seeding campaign. Catalog rows are placeholders until the Authority short list lands.",
        "authority_contact_note_ar": "تواصل مع سلطة الحراجة الزراعية قبل أي حملة بذر. صفوف الكتالوج مؤقتة حتى تصل القائمة القصيرة المعتمدة.",
        "science_lock": SCIENCE_LOCK,
        "domains": [DOMAIN_AGRICULTURE, DOMAIN_MOUNTAIN],
        "never_mix_domains": True,
        "forbidden": list(FORBIDDEN),
        "species": species,
        "honesty_note_en": "Species lists are unvalidated expert stubs. Domains never mixed. Not operational truth. No campaign quantities.",
        "honesty_note_ar": "قوائم الأنواع مسودات خبير غير مُتحقَّقة. المجالات لا تُخلط. ليست حقيقة تشغيلية. بلا كميات حملة.",
    }


def species_for_domain(catalog: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    if domain not in (DOMAIN_AGRICULTURE, DOMAIN_MOUNTAIN):
        raise ValueError(f"unknown seed domain: {domain}")
    return [s for s in catalog["species"] if s["domain"] == domain]


def _timing_for_domain(domain: str) -> dict[str, Any]:
    if domain == DOMAIN_AGRICULTURE:
        return {
            "kind": "calendar_heuristic",
            "status": "provisional",
            "window_label_en": "Najd cool-season heuristic (approx Nov–Mar) — provisional calendar only",
            "window_label_ar": "إرشاد موسم نجد البارد (تقريباً نوفمبر–مارس) — تقويم مؤقت فقط",
            "note_en": "Calendar heuristic provisional — not phenology engine output; not live onset.",
            "live_khareef_onset": False,
        }
    return {
        "kind": "calendar_heuristic",
        "status": "provisional",
        "window_label_en": "Post-khareef heuristic (late Sep–Oct preference) — provisional; not live onset",
        "window_label_ar": "إرشاد ما بعد الخريف (أواخر سبتمبر–أكتوبر) — مؤقت؛ ليس رصد بداية حي",
        "note_en": "Calendar heuristic provisional — MPI/onset labeling locks still apply; no live Khareef onset.",
        "live_khareef_onset": False,
    }


def _base_gaps(domain: str, site_ref: str) -> list[str]:
    gaps = [
        "authority_short_list_pending",
        "no_field_validation",
        "species_suitability_unvalidated",
        "no_campaign_quantities_by_design",
    ]
    if domain == DOMAIN_AGRICULTURE:
        gaps.extend(
            [
                "no_aou_ground_truth_species",
                f"site_ref={site_ref}",
            ]
        )
    else:
        gaps.extend(
            [
                "mountain_partner_ui_forbidden_until_resignoff",
                "post_khareef_re_signoff_pending",
                "mpi_sample_cell_not_validated_planting_site",
                f"site_ref={site_ref}",
            ]
        )
    return gaps


def build_matrix_row(
    *,
    site_ref: str,
    domain: str,
    species: dict[str, Any],
) -> dict[str, Any]:
    """One Site × Species scaffold row — no cross-domain path."""
    if species["domain"] != domain:
        raise ValueError(
            f"cross-domain blocked: site domain={domain} species={species['species_id']} "
            f"species_domain={species['domain']}"
        )
    if domain not in (DOMAIN_AGRICULTURE, DOMAIN_MOUNTAIN):
        raise ValueError(f"unknown seed domain: {domain}")

    return {
        "site_ref": site_ref,
        "domain": domain,
        "species_id": species["species_id"],
        "species_name_sci": species["species_name_sci"],
        "suitability_provisional_0_100": None,
        "status": STATUS_UNVALIDATED,
        "evidence_gaps": _base_gaps(domain, site_ref),
        "species_suitability": {
            "status": "unvalidated",
            "score_0_100": None,
            "note_en": "Matrix scaffold only — unvalidated; not operational truth.",
            "note_ar": "هيكل مصفوفة فقط — غير مُتحقَّق؛ ليست حقيقة تشغيلية.",
        },
        "seed_recommendation": {
            "mode": "manual",
            "operator_confirmed": False,
            "recommendation_text_en": None,
            "recommendation_text_ar": None,
            "note_en": "Manual / operator-confirmed only — no auto recommend.",
        },
        "timing_window": _timing_for_domain(domain),
        "seed_provenance": {
            "local_preferred": bool(species.get("local_preferred", False)),
            "provenance_status": (
                "local_preferred_flag_only"
                if species.get("local_preferred")
                else "authority_pending"
            ),
            "note_en": "local_preferred flag only — not a verified lot certificate.",
        },
        "seeding_protocol": {
            "mode": "manual_operator_confirmed",
            "steps": list(PROTOCOL_STEPS),
            "auto_assign": False,
            "note_en": "Enum steps only; operator must confirm. No auto campaign planner.",
        },
    }


def build_agriculture_rows(
    catalog: dict[str, Any], aou_ids: list[str]
) -> list[dict[str, Any]]:
    """Najd path — AOU registry sites × agriculture_aou species only."""
    species = species_for_domain(catalog, DOMAIN_AGRICULTURE)
    rows: list[dict[str, Any]] = []
    for aou_id in aou_ids:
        for sp in species:
            rows.append(
                build_matrix_row(
                    site_ref=aou_id, domain=DOMAIN_AGRICULTURE, species=sp
                )
            )
    return rows


def build_mountain_rows(
    catalog: dict[str, Any], site_refs: list[str]
) -> list[dict[str, Any]]:
    """Mountain path — sample cells × restoration_mountain species only.

    Offline notes OK. Do NOT wire to partner mountain Decision UI.
    """
    species = species_for_domain(catalog, DOMAIN_MOUNTAIN)
    rows: list[dict[str, Any]] = []
    for site_ref in site_refs:
        for sp in species:
            rows.append(
                build_matrix_row(
                    site_ref=site_ref, domain=DOMAIN_MOUNTAIN, species=sp
                )
            )
    return rows


def build_site_species_matrix(rows: list[dict[str, Any]]) -> dict[str, Any]:
    # Integrity: no cross-domain leakage inside a row
    for r in rows:
        if r["domain"] == DOMAIN_AGRICULTURE and r["species_id"] == "terminalia_dhofarica":
            raise RuntimeError("forbidden: T. dhofarica on agriculture_aou row")
        if r["domain"] == DOMAIN_MOUNTAIN and r["species_id"] in {
            "ziziphus_spina_christi",
            "vachellia_tortilis",
            "prosopis_cineraria",
            "irrigated_fodder_placeholder",
        }:
            raise RuntimeError("forbidden: Najd species on restoration_mountain row")
        for banned in ("campaign_ha", "seed_kg", "crew_days"):
            if banned in r:
                raise RuntimeError(f"forbidden field present: {banned}")

    return {
        "version": "0.4.4-phase4-seed-scaffold",
        "status": STATUS_UNVALIDATED,
        "science_lock": SCIENCE_LOCK,
        "never_mix_domains": True,
        "suitability_neq_confidence": True,
        "writes_to_app_public": False,
        "mountain_partner_ui": False,
        "forbidden": list(FORBIDDEN),
        "rows": rows,
        "honesty_note_en": (
            "Site × Species matrix scaffold. Scores null/unvalidated. "
            "Domains agriculture_aou vs restoration_mountain never mixed. "
            "No campaign quantities. No Map/Restoration Seed UI in this artifacts PR."
        ),
        "honesty_note_ar": (
            "هيكل مصفوفة موقع×نوع. الدرجات فارغة/غير مُتحقَّقة. "
            "المجالان agriculture_aou و restoration_mountain لا يُخلطان. "
            "بلا كميات حملة. بلا واجهة بذر في هذا الـPR."
        ),
    }


def build_seed_intelligence_wrapper() -> dict[str, Any]:
    return {
        "version": "0.4.4-phase4-seed-scaffold",
        "status": STATUS_UNVALIDATED,
        "science_lock": SCIENCE_LOCK,
        "domains": [DOMAIN_AGRICULTURE, DOMAIN_MOUNTAIN],
        "never_mix_domains": True,
        "suitability_neq_confidence": True,
        "species_catalog_ref": "satellite/pipeline/artifacts/seed/species_catalog.json",
        "site_species_matrix_ref": "satellite/pipeline/artifacts/seed/site_species_matrix.json",
        "seeding_protocol_stubs": {
            "mode": "manual_operator_confirmed",
            "auto_assign": False,
            "steps_enum": list(PROTOCOL_STEPS),
            "labels": PROTOCOL_LABELS,
            "note_en": "Manual / operator-confirmed protocol enum only — no auto campaign planner.",
        },
        "forbidden": list(FORBIDDEN),
        "ui_gates": {
            "analysis_seed_panel": False,
            "restoration_seed_panel": False,
            "mountain_partner_ui": False,
            "writes_to_app_public": False,
            "link_mountain_decision_to_species_candidates": False,
        },
        "authority_source": AUTHORITY_SOURCE,
        "honesty_note_en": (
            "Seed Intelligence does: Site×Species scaffold, domain-separated short lists, "
            "manual protocol stubs. Does NOT: operational suitability scores, campaign ha/kg/crew, "
            "mountain partner UI, pest/soil%/live Khareef, cross-domain recommend."
        ),
        "honesty_note_ar": (
            "ذكاء البذور يفعل: هيكل موقع×نوع وقوائم مفصولة وبروتوكول يدوي. "
            "لا يفعل: درجات تشغيلية، كميات حملة، واجهة جبل شريكة، آفات/رطوبة تربة%/خريف حي، توصية عبر المجالات."
        ),
    }
