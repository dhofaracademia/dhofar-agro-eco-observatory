#!/usr/bin/env python3
"""Phase-3 Decision Engine scaffolds — agriculture AOU only (offline artifacts).

Reads Phase-1 AOU registry + observations from app/public/data/aou/ (inputs only)
and writes decision artifacts under satellite/pipeline/artifacts/decision/.

NEVER writes Suitability / Confidence / Evidence Gap into app/public/
until science re-sign-off.

HARD GATES:
  - Suitability ≠ Confidence ≠ data_quality_confidence — never merge
  - mountain_apply = false (do not apply agriculture_aou weights to mountain)
  - action_auto_assign = false; action_ladder_suggestion = null
  - No mountain partner UI
  - No campaign numbers, pest certainty, soil moisture %, live Khareef
  - MPI onset narrative (if referenced) = onset-T0 provisional only
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AOU_DIR = ROOT / "app" / "public" / "data" / "aou"
OUT_DIR = Path(__file__).resolve().parent / "artifacts" / "decision"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engines.suitability import compute_suitability  # noqa: E402
from engines.confidence import compute_confidence  # noqa: E402
from engines.evidence_gap import assess_evidence_gaps  # noqa: E402


ACTION_LADDER_STUBS = {
    "schema_ref": "docs/spec_0.4/action_ladder.schema.json",
    "science_lock": "SCIENCE_LOCKS_v0.4_phase1_2.md§Phase3",
    "status": "enum_and_manual_only",
    "provisional": True,
    "manual_only": True,
    "auto_assign_from_suitability": False,
    "action_ladder_suggestion": None,
    "domain": "agriculture_aou_decision",
    "mountain_apply": False,
    "forbidden": [
        "numeric_suitability_to_action_auto_assignment",
        "campaign_hectares_as_official",
        "pest_certainty",
        "soil_moisture_percent",
        "merge_suitability_and_confidence",
        "apply_agriculture_aou_weights_to_mountain",
    ],
    "ladder_enum": [
        "field_irrigation_inspection",
        "field_vigor_inspection",
        "biotic_field_verification",
        "continue_monitoring",
        "defer_insufficient_evidence",
    ],
    "labels": {
        "field_irrigation_inspection": {
            "en": "Field irrigation inspection",
            "ar": "معاينة ري ميدانية",
            "order": 1,
        },
        "field_vigor_inspection": {
            "en": "Field vigor inspection",
            "ar": "معاينة حيوية ميدانية",
            "order": 2,
        },
        "biotic_field_verification": {
            "en": "Biotic field verification",
            "ar": "تحقق ميداني لإجهاد حيوي محتمل",
            "order": 3,
        },
        "continue_monitoring": {
            "en": "Continue monitoring",
            "ar": "متابعة الرصد",
            "order": 4,
        },
        "defer_insufficient_evidence": {
            "en": "Defer — insufficient evidence",
            "ar": "تأجيل — أدلة غير كافية",
            "order": 5,
        },
    },
    "rule_stubs": [
        {
            "id": "stub_irrigation",
            "ladder": "field_irrigation_inspection",
            "rule_stub_en": "When moisture_proxy is low (high water_stress), experts may manually choose irrigation inspection. Auto-assign FORBIDDEN.",
            "rule_stub_ar": "عند انخفاض moisture_proxy يمكن للخبير اختيار معاينة الري يدوياً. التعيين التلقائي ممنوع.",
            "requires_field_validation": True,
            "auto_assign_from_suitability": False,
        },
        {
            "id": "stub_vigor",
            "ladder": "field_vigor_inspection",
            "rule_stub_en": "When vigor_proxy is low, manual vigor inspection — not fertilizer diagnosis.",
            "rule_stub_ar": "عند انخفاض vigor_proxy معاينة حيوية يدوية — وليست تشخيص سماد.",
            "requires_field_validation": True,
            "auto_assign_from_suitability": False,
        },
        {
            "id": "stub_biotic",
            "ladder": "biotic_field_verification",
            "rule_stub_en": "possible_biotic_stress flag only — never pest name; field verification recommended.",
            "rule_stub_ar": "علم possible_biotic_stress فقط — بلا اسم آفة؛ يُوصى بالتحقق الميداني.",
            "requires_field_validation": True,
            "auto_assign_from_suitability": False,
        },
        {
            "id": "stub_monitor",
            "ladder": "continue_monitoring",
            "rule_stub_en": "Default when scores are mid-range or history is thin — continue Phase-1 monitor.",
            "rule_stub_ar": "الافتراضي عند درجات متوسطة أو تاريخ ضعيف — متابعة رصد المرحلة 1.",
            "requires_field_validation": True,
            "auto_assign_from_suitability": False,
        },
        {
            "id": "stub_defer",
            "ladder": "defer_insufficient_evidence",
            "rule_stub_en": "When Evidence Gap is large (no field visit, thin history, missing scores) — defer.",
            "rule_stub_ar": "عند فجوة أدلة كبيرة — تأجيل.",
            "requires_field_validation": True,
            "auto_assign_from_suitability": False,
        },
    ],
    "note_en": "Display enum / manual recommended next step only. Pipeline leaves action_ladder_suggestion null.",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _latest_obs(unit: dict) -> dict | None:
    obs = unit.get("observations") or []
    if not obs:
        return None
    return sorted(obs, key=lambda o: o.get("date") or "")[-1]


def _n_clear_dates(unit: dict) -> int:
    """Count AOU-scoped observations (not window stubs)."""
    n = 0
    for o in unit.get("observations") or []:
        if o.get("date") and o.get("series_scope") != "window_not_aou":
            n += 1
    return n


def _window_stub_only(unit: dict) -> bool:
    obs = unit.get("observations") or []
    aou_dates = [o for o in obs if o.get("series_scope") != "window_not_aou"]
    ctx = unit.get("window_context_series") or []
    return len(aou_dates) <= 1 and len(ctx) > 0


def main() -> int:
    registry_path = AOU_DIR / "aou_registry.json"
    obs_path = AOU_DIR / "aou_observations.json"
    if not registry_path.exists() or not obs_path.exists():
        print(f"ERROR: missing AOU inputs under {AOU_DIR}", file=sys.stderr)
        return 1

    registry = _load_json(registry_path)
    observations = _load_json(obs_path)
    units_by_id = {u["aou_id"]: u for u in observations.get("units") or []}
    reg_by_id = {u["aou_id"]: u for u in registry.get("units") or []}

    suitability_units: list[dict] = []
    confidence_units: list[dict] = []
    evidence_units: list[dict] = []

    aou_ids = sorted(set(reg_by_id) | set(units_by_id))
    for aou_id in aou_ids:
        reg = reg_by_id.get(aou_id) or {}
        unit = units_by_id.get(aou_id) or {}
        latest = _latest_obs(unit) or {}
        n_clear = _n_clear_dates(unit)
        prior_ids = reg.get("previous_ids") or []
        is_new = len(prior_ids) == 0
        prior_iou = None  # Phase-1 registry does not yet persist IoU; honest null
        area_ha = latest.get("area_ha_est")
        if area_ha is None:
            area_ha = reg.get("area_ha_est")
        prior_seasons = 0  # no multi-season depth yet
        ndre_available = latest.get("ndre_available")
        if ndre_available is None:
            ndre_available = bool(latest.get("ndre") is not None)

        gaps = assess_evidence_gaps(
            aou_id=aou_id,
            ndre_available=ndre_available,
            has_field_visit=False,
            n_aou_observations=n_clear,
            prior_seasons_count=prior_seasons,
            prior_iou=prior_iou,
            has_post_khareef_clear=False,
            has_mpi_curve=False,
            window_series_stub_only=_window_stub_only(unit),
            data_quality_confidence=latest.get("data_quality_confidence"),
            agricultural_probability=latest.get("agricultural_probability", reg.get("agricultural_probability")),
            water_stress_score=latest.get("water_stress_score"),
            vigor_stress_score=latest.get("vigor_stress_score"),
            observation_date=latest.get("date"),
        )
        evidence_units.append(gaps)

        suit = compute_suitability(
            aou_id=aou_id,
            agricultural_probability=latest.get(
                "agricultural_probability", reg.get("agricultural_probability")
            ),
            water_stress_score=latest.get("water_stress_score"),
            vigor_stress_score=latest.get("vigor_stress_score"),
            ndvi_persistence=None,
            n_clear_dates=n_clear,
            prior_iou=prior_iou,
            area_ha=area_ha,
            observation_date=latest.get("date"),
            product_id=latest.get("product_id"),
            tile=latest.get("tile"),
            source=latest.get("source"),
            ndre_available=ndre_available,
            evidence_gap_codes=gaps.get("missing_input_codes") or [],
        )
        suitability_units.append(suit)

        conf = compute_confidence(
            aou_id=aou_id,
            data_quality_confidence=latest.get("data_quality_confidence"),
            n_clear_dates=n_clear,
            prior_seasons_count=prior_seasons,
            prior_iou=prior_iou,
            is_new_id=is_new,
            observation_date=latest.get("date"),
            product_id=latest.get("product_id"),
        )
        confidence_units.append(conf)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()

    common_meta = {
        "version": "0.4.3-phase3-scaffolds",
        "generated_at": generated_at,
        "formula_ref": "SCIENCE_LOCKS_v0.4_phase1_2.md§Phase3",
        "status": "expert_v1_provisional",
        "never_merge": True,
        "mountain_apply": False,
        "action_auto_assign": False,
        "writes_to_app_public": False,
        "input_refs": {
            "aou_registry": str(registry_path.relative_to(ROOT)),
            "aou_observations": str(obs_path.relative_to(ROOT)),
        },
        "honesty_en": (
            "Offline decision scaffolds for Najd agriculture AOUs only. "
            "Suitability ≠ Confidence ≠ data_quality_confidence. "
            "Not ecological certainty. No mountain UI. Action ladder manual only."
        ),
    }

    suit_doc = {
        **common_meta,
        "schema_ref": "docs/spec_0.4/suitability_components.schema.json",
        "suitability_domain": "agriculture_aou",
        "suitability_summary_label": "components_only",
        "units": suitability_units,
    }
    conf_doc = {
        **common_meta,
        "schema_ref": "docs/spec_0.4/confidence.schema.json",
        "confidence_domain": "data_evidence",
        "not_ecological_certainty": True,
        "units": confidence_units,
    }
    gap_doc = {
        **common_meta,
        "schema_ref": "docs/spec_0.4/evidence_gap.schema.json",
        "units": evidence_units,
    }

    files = {
        "aou_suitability_components.json": suit_doc,
        "aou_confidence.json": conf_doc,
        "aou_evidence_gaps.json": gap_doc,
        "action_ladder.stubs.json": ACTION_LADDER_STUBS,
        "run_meta.json": {
            **common_meta,
            "artifact_files": [
                "aou_suitability_components.json",
                "aou_confidence.json",
                "aou_evidence_gaps.json",
                "action_ladder.stubs.json",
            ],
            "aou_count": len(aou_ids),
            "engines": [
                "engines/suitability.py",
                "engines/confidence.py",
                "engines/evidence_gap.py",
            ],
            "ui_gate": "Analysis Decision UI chrome deferred — artifacts-first PR",
            "mpi_note_en": (
                "If MPI is referenced: onset-T0 provisional only — "
                "do not label as post-khareef for agriculture AOUs."
            ),
        },
    }

    for name, doc in files.items():
        path = OUT_DIR / name
        with path.open("w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"wrote {path.relative_to(ROOT)}")

    print(f"OK — {len(aou_ids)} AOUs → {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
