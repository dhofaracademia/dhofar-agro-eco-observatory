"""Evidence Gap — Phase-3 Decision Engine.

Lists missing inputs honestly. Does not invent campaign numbers, pest names,
soil moisture %, live Khareef, or post-khareef clear MPI for Najd AOUs.
"""

from __future__ import annotations

from typing import Any

STATUS = "expert_v1_provisional"
FORMULA_REF = "SCIENCE_LOCKS_v0.4_phase1_2.md§Phase3"

FORBIDDEN_CLAIMS = [
    "campaign_hectares_as_official",
    "pest_name_or_certainty",
    "soil_moisture_percent",
    "live_khareef_onset",
    "suitability_merged_with_confidence",
    "action_auto_assigned_from_suitability",
    "mpi_as_post_khareef_for_agriculture_aou",
]

# Catalog of gap checks (id, code, severity, en, ar) — evaluated against inputs
_GAP_CATALOG = [
    (
        "gap_ndre",
        "no_ndre",
        "caution",
        "No NDRE (red-edge) on this observation — AgProb may have renormed.",
        "لا يوجد NDRE (الحافة الحمراء) في هذه الملاحظة — قد يُعاد توزيع وزن الاحتمال الزراعي.",
    ),
    (
        "gap_field",
        "no_field_visit",
        "caution",
        "No dated field visit on file — optional additional field verification (last resort) only; not a prerequisite to act.",
        "لا زيارة ميدانية مؤرخة — معاينة ميدانية لاحقة اختيارية للتحقق الإضافي فقط؛ ليست شرطاً للاستخدام.",
    ),
    (
        "gap_history",
        "thin_aou_history",
        "caution",
        "AOU multi-date history is thin (≤1 clear AOU observation).",
        "تاريخ الوحدة متعدد التواريخ ضعيف (≤1 ملاحظة صافية).",
    ),
    (
        "gap_seasons",
        "no_historical_seasons",
        "caution",
        "No prior-season historical anomaly depth for this AOU.",
        "لا عمق مواسم سابقة لشذوذ تاريخي لهذه الوحدة.",
    ),
    (
        "gap_iou",
        "no_prior_iou",
        "info",
        "No prior IoU match (new or unmatched ID).",
        "لا تطابق IoU سابق (معرّف جديد أو غير مطابق).",
    ),
    (
        "gap_post_khareef",
        "no_post_khareef_clear",
        "info",
        "No post-khareef clear composite attached (agriculture AOU path — not mountain MPI).",
        "لا مركّب صافٍ بعد الخريف مرتبط (مسار وحدات الزراعة — وليس MPI الجبلي).",
    ),
    (
        "gap_mpi",
        "no_mpi_curve",
        "info",
        "No MPI curve on this agriculture AOU (MPI is mountain offline evidence; onset-T0 provisional only).",
        "لا منحنى MPI على وحدة الزراعة هذه (MPI أدلة جبلية دون اتصال؛ بداية T0 مؤقتة فقط).",
    ),
    (
        "gap_window_stub",
        "window_series_stub_only",
        "caution",
        "Temporal context still includes window-level stub series (not AOU-specific multi-date).",
        "السياق الزمني ما زال يتضمن سلسلة نافذة تقريبية (وليست متعددة التواريخ للوحدة).",
    ),
    (
        "gap_dq",
        "low_data_quality",
        "caution",
        "Data-quality confidence is low (<40).",
        "ثقة جودة البيانات منخفضة (<40).",
    ),
    (
        "gap_agprob",
        "missing_ag_probability",
        "blocking",
        "Agricultural probability missing on this record.",
        "الاحتمال الزراعي مفقود في هذا السجل.",
    ),
    (
        "gap_stress",
        "missing_stress_scores",
        "caution",
        "Water and/or vigor stress scores missing.",
        "درجات إجهاد الماء و/أو الحيوية مفقودة.",
    ),
]


def assess_evidence_gaps(
    *,
    aou_id: str,
    ndre_available: bool | None = None,
    has_field_visit: bool = False,
    n_aou_observations: int | None = None,
    prior_seasons_count: int | None = None,
    prior_iou: float | None = None,
    has_post_khareef_clear: bool = False,
    has_mpi_curve: bool = False,
    window_series_stub_only: bool | None = None,
    data_quality_confidence: float | None = None,
    agricultural_probability: float | None = None,
    water_stress_score: float | None = None,
    vigor_stress_score: float | None = None,
    observation_date: str | None = None,
) -> dict[str, Any]:
    """Build honest evidence_gaps[] for one AOU."""
    # present=True means input IS available; present=False means gap
    # present=True means the INPUT is available (not a gap).
    # For codes named no_*, present=True means the thing is NOT missing.
    if window_series_stub_only is None:
        window_ok = False  # unknown → treat as gap (fail-honest)
    else:
        window_ok = not bool(window_series_stub_only)

    flags: dict[str, bool] = {
        "no_ndre": bool(ndre_available) if ndre_available is not None else False,
        "no_field_visit": bool(has_field_visit),
        "thin_aou_history": bool(n_aou_observations is not None and n_aou_observations > 1),
        "no_historical_seasons": bool(prior_seasons_count is not None and prior_seasons_count >= 1),
        "no_prior_iou": prior_iou is not None,
        "no_post_khareef_clear": bool(has_post_khareef_clear),
        "no_mpi_curve": bool(has_mpi_curve),
        "window_series_stub_only": window_ok,
        "low_data_quality": not (
            data_quality_confidence is not None and float(data_quality_confidence) < 40
        ),
        "missing_ag_probability": agricultural_probability is not None,
        "missing_stress_scores": (
            water_stress_score is not None and vigor_stress_score is not None
        ),
    }

    gaps: list[dict[str, Any]] = []
    for gid, code, severity, en, ar in _GAP_CATALOG:
        is_present = flags.get(code, False)
        gaps.append(
            {
                "id": gid,
                "code": code,
                "present": is_present,
                "severity_en": en if not is_present else en.replace("No ", "Has ").replace("لا ", "يتوفر — كان: لا "),
                "severity_ar": ar if not is_present else f"متوفر — ({ar})",
                "severity": severity if not is_present else "info",
            }
        )
        # Cleaner severity text when present: keep original severity only for gaps
        if is_present:
            gaps[-1]["severity_en"] = f"OK — {code} input available."
            gaps[-1]["severity_ar"] = f"حسناً — المدخل {code} متوفر."
            gaps[-1]["severity"] = "info"

    missing = [g["code"] for g in gaps if not g["present"]]
    return {
        "aou_id": aou_id,
        "status": STATUS,
        "evidence_gaps": gaps,
        "missing_input_codes": missing,
        "gap_count": len(missing),
        "honesty_note_en": (
            "Evidence Gap lists missing inputs honestly. "
            "Does not invent campaign numbers, pest certainty, soil moisture %, or live Khareef. "
            "MPI onset narrative (if any) is onset-T0 provisional only — not post-khareef labeling for AOUs."
        ),
        "honesty_note_ar": (
            "فجوة الأدلة تسرد المدخلات الناقصة بصدق. "
            "لا تختلق أرقام حملات أو يقين آفات أو رطوبة تربة % أو خريفاً حياً. "
            "سرد بداية MPI (إن وُجد) مؤقت عند T0 فقط — وليس وسم ما بعد الخريف لوحدات الزراعة."
        ),
        "forbidden_claims": list(FORBIDDEN_CLAIMS),
        "cite_slots": {
            "formula_ref": FORMULA_REF,
            "observation_date": observation_date,
        },
    }
