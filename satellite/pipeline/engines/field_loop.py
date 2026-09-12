"""Phase-5 Field Loop scaffold — SCIENCE_LOCKS_v0.4_phase5_field_loop.

Capture only. Domains never mix. Phase-4 six species only.
Germination ≠ establishment ≠ survival. Satellite ≠ germination meter.
Missed ≠ failure (no interpolate). No fabricated rates.
No auto-rewrite Suitability / Confidence / Site×Species.
Mountain UI Hold. No partner Field UI. No Authority-approved wording.
Photos: optional plot evidence; no children / ID docs / face recognition.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIR.parents[1]
SCAFFOLD_PATH = REPO_ROOT / "docs" / "phase5_field_loop_scaffold.json"
PHASE4_SCAFFOLD = REPO_ROOT / "docs" / "phase4_species_scaffold.json"
OUT_DIR = PIPELINE_DIR / "artifacts" / "field"

SCIENCE_LOCK = "SCIENCE_LOCKS_v0.4_phase5_field_loop"
VETTING = "scientist_locked_pending_ea"

ALLOWED_SPECIES = (
    "sp-fog-tdhof",
    "sp-fog-oleac",
    "sp-fog-fsyco",
    "sp-najd-zsc",
    "sp-najd-vtor",
    "sp-najd-pcin",
)

SPECIES_DOMAIN = {
    "sp-fog-tdhof": "fog_escarpment",
    "sp-fog-oleac": "fog_escarpment",
    "sp-fog-fsyco": "fog_escarpment",
    "sp-najd-zsc": "najd_arid",
    "sp-najd-vtor": "najd_arid",
    "sp-najd-pcin": "najd_arid",
}

BROADCAST_OVERRIDE_SPECIES = frozenset({"sp-fog-oleac", "sp-fog-fsyco"})

FOG_TIMING = frozenset({"late_khareef", "early_post_khareef", "deferred"})
NAJD_TIMING = frozenset({"winter_spring_rain", "irrigated"})
PLANTING_INTERVENTIONS = frozenset(
    {"seeding", "enrichment_seeding", "planting", "vegetative"}
)

VISIT_WINDOWS: dict[str, tuple[int | None, int | None, int | None]] = {
    # visit_type: (center_day, min, max) — ad_hoc has no window
    "baseline": (0, -7, 0),
    "d30_germination": (30, 21, 45),
    "d90_survival": (90, 75, 105),
    "d180_establishment": (180, 160, 200),
    "d365_survival": (365, 335, 395),
    "ad_hoc": (None, None, None),
}

SCHEDULED_VISIT_TYPES = (
    "baseline",
    "d30_germination",
    "d90_survival",
    "d180_establishment",
    "d365_survival",
)

GERMINATION_NA_MODES = frozenset({"protect_regeneration", "vegetative_preferred"})
GERMINATION_NA_METHODS = frozenset(
    {"seedling", "cutting", "wilding", "protection_only"}
)

DISCLAIMER_EN = (
    "Field log — germination ≠ establishment ≠ survival. "
    "Not a platform success score, not an Environment Authority approval."
)
DISCLAIMER_AR = (
    "سجل ميداني — إنبات ≠ تأسيس ≠ بقاء. "
    "ليست درجة نجاح للمنصة وليست اعتماداً من هيئة البيئة."
)

FORBIDDEN = [
    "domain_mix",
    "species_outside_phase4_six",
    "blocked_exotic",
    "campaign_ha",
    "seed_kg",
    "crew_days",
    "kg_per_ha",
    "germination_pct_operational",
    "survival_pct_operational",
    "recommendation_success",
    "species_failed_auto",
    "site_failed_auto",
    "interpolate_missed_counts",
    "satellite_as_germination_meter",
    "auto_rewrite_suitability_confidence_matrix",
    "Authority-approved",
    "معتمد من الهيئة",
    "partner_field_ui",
    "mountain_partner_ui",
    "partner_photo_gallery",
    "face_recognition",
    "auto_species_id_from_photo",
    "photos_of_children",
    "identity_documents",
    "phase6_learning",
]


def load_scaffold() -> dict[str, Any]:
    return json.loads(SCAFFOLD_PATH.read_text(encoding="utf-8"))


def load_species_domain_map() -> dict[str, str]:
    """Tip-update: prefer Phase-4 scaffold if present; else built-in map."""
    if PHASE4_SCAFFOLD.exists():
        doc = json.loads(PHASE4_SCAFFOLD.read_text(encoding="utf-8"))
        out: dict[str, str] = {}
        for s in doc.get("species", []):
            if s.get("scaffold_include") and s.get("species_id") and s.get("domain"):
                out[s["species_id"]] = s["domain"]
        if out:
            return out
    return dict(SPECIES_DOMAIN)


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def days_since(event_date: date, visit_date: date) -> int:
    return (visit_date - event_date).days


def window_status_for(
    visit_type: str, days_since_event: int | None, *, has_visit: bool
) -> str:
    """Compute window_status. ad_hoc never closes a scheduled window."""
    if visit_type == "ad_hoc":
        return "on_window" if has_visit else "missed"
    center, lo, hi = VISIT_WINDOWS[visit_type]
    assert lo is not None and hi is not None
    if days_since_event is None:
        return "missed"
    if lo <= days_since_event <= hi:
        return "on_window"
    if days_since_event < lo:
        return "early"
    # after window close
    if has_visit:
        return "late"
    return "missed"


def germination_not_applicable(event: dict[str, Any]) -> bool:
    mode = event.get("establishment_mode")
    method = event.get("method")
    intervention = event.get("intervention_type")
    if mode in GERMINATION_NA_MODES:
        return True
    if method in GERMINATION_NA_METHODS:
        return True
    if intervention in {"vegetative", "protect_regeneration"}:
        return True
    return False


def validate_seeding_event(event: dict[str, Any]) -> list[str]:
    """Return reject reasons (empty = valid). Tip-update point for mid-flight locks."""
    reasons: list[str] = []
    domain_map = load_species_domain_map()
    sid = event.get("species_id")
    domain = event.get("domain")

    if sid not in ALLOWED_SPECIES and sid not in domain_map:
        reasons.append("species_id_not_in_six")
    expected = domain_map.get(sid) or SPECIES_DOMAIN.get(sid)
    if expected and domain != expected:
        reasons.append("domain_ne_species_domain")
    if domain not in {"fog_escarpment", "najd_arid"}:
        reasons.append("invalid_domain")

    if not event.get("event_date"):
        reasons.append("missing_event_date")
    gps = event.get("gps") or {}
    if gps.get("lat") is None or gps.get("lon") is None:
        reasons.append("missing_gps")

    if event.get("provenance_class") == "blocked_exotic":
        reasons.append("provenance_class_blocked_exotic")

    if (
        event.get("method") == "broadcast"
        and sid in BROADCAST_OVERRIDE_SPECIES
        and not (event.get("override_note") or "").strip()
    ):
        reasons.append("broadcast_on_oleac_or_fsyco_without_override_note")

    timing = event.get("timing_window")
    if domain == "fog_escarpment":
        if timing not in FOG_TIMING:
            reasons.append("invalid_fog_timing_window")
        if timing == "deferred" and event.get("intervention_type") in PLANTING_INTERVENTIONS:
            if event.get("event_status") != "cancelled":
                reasons.append("fog_planting_while_timing_deferred")
    elif domain == "najd_arid":
        if timing not in NAJD_TIMING:
            reasons.append("invalid_najd_timing_window")

    if event.get("vetting_status") != VETTING:
        reasons.append("vetting_status_must_be_scientist_locked_pending_ea")

    qty = event.get("quantity")
    if qty is not None:
        if qty.get("source") != "operator_reported_unvalidated":
            reasons.append("quantity_source_must_be_operator_reported_unvalidated")
        if qty.get("unit") not in {"seeds", "seedlings", "cuttings", "grams"}:
            reasons.append("invalid_quantity_unit")

    for banned in ("campaign_ha", "seed_kg", "crew_days"):
        if event.get(banned) is not None:
            reasons.append(f"{banned}_must_be_null")

    return reasons


def planned_date(event_date: date, center_day: int) -> date:
    return event_date + timedelta(days=center_day)


def muscat_today() -> date:
    """Asia/Muscat calendar day for clock-aware window_status."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Muscat")).date()
    except Exception:
        return datetime.now(timezone.utc).date()


def planned_window_status(
    visit_type: str,
    event_date: date,
    *,
    as_of: date | None = None,
    has_dated_visit: bool = False,
) -> str:
    """Clock-aware status for planned stubs with no dated visit yet.

    - Do NOT stamp missed until window_day_max has passed with no visit.
    - Before window opens: early
    - Inside window: on_window
    - After window closes with no visit: missed
    - After window with a late visit: late (caller sets has_dated_visit)
    """
    if visit_type == "ad_hoc":
        return "on_window" if has_dated_visit else "missed"
    _center, lo, hi = VISIT_WINDOWS[visit_type]
    assert lo is not None and hi is not None
    as_of = as_of or muscat_today()
    days = (as_of - event_date).days
    if has_dated_visit:
        return window_status_for(visit_type, days, has_visit=True)
    if days < lo:
        return "early"
    if lo <= days <= hi:
        return "on_window"
    return "missed"


def create_planned_followups(
    event: dict[str, Any],
    *,
    obs_seq_start: int = 1,
    year: int | None = None,
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    """Create scheduled follow-up stubs from event_date (no fabricated outcomes).

    - Germination visit: outcome_class=not_applicable when protect/vegetative/etc.
    - window_status is clock-aware (Asia/Muscat): early | on_window | missed
      — never mark future/open windows as missed.
    - Never invent germination_pct / survival_pct.
    """
    rejects = validate_seeding_event(event)
    if rejects:
        raise ValueError(f"invalid seeding event {event.get('event_id')}: {rejects}")

    ed = parse_iso_date(event["event_date"])
    y = year or ed.year
    as_of = as_of or muscat_today()
    germ_na = germination_not_applicable(event)
    rows: list[dict[str, Any]] = []
    seq = obs_seq_start

    for visit_type in SCHEDULED_VISIT_TYPES:
        center, lo, hi = VISIT_WINDOWS[visit_type]
        assert center is not None and lo is not None and hi is not None
        planned = planned_date(ed, center)
        status = planned_window_status(visit_type, ed, as_of=as_of, has_dated_visit=False)

        if visit_type == "d30_germination" and germ_na:
            outcome = "not_applicable"
            # outcome_class carries science; do not brand N/A as missed
            status = "on_window"
            notes = (
                "Germination not_applicable (not zero) for "
                f"establishment_mode={event.get('establishment_mode')} "
                f"method={event.get('method')} "
                f"intervention_type={event.get('intervention_type')}."
            )
        else:
            outcome = "not_observed"
            notes = (
                f"Scheduled window stub (as_of={as_of.isoformat()}, "
                f"window_days={lo}..{hi}, day={(as_of - ed).days}) — "
                f"status={status}. missed ≠ failure; do not interpolate; "
                "no fabricated rates. Only stamp missed after window_day_max."
            )

        rows.append(
            {
                "observation_id": f"FO-{y}-{seq:06d}",
                "event_id": event["event_id"],
                "visit_type": visit_type,
                "visit_date": None,
                "planned_at": planned.isoformat(),
                "days_since_event": (as_of - ed).days,
                "window_day_min": lo,
                "window_day_max": hi,
                "window_status": status,
                "outcome_class": outcome,
                "observer": "scheduler_stub",
                "target_count": None,
                "photos": [],
                "notes": notes,
                "vetting_status": VETTING,
                "honesty_note_en": DISCLAIMER_EN,
                "honesty_note_ar": DISCLAIMER_AR,
            }
        )
        seq += 1
    return rows


def build_field_loop_wrapper(
    *,
    events_ref: str = "seeding_events.sample.json",
    observations_ref: str = "field_observations.sample.json",
    csv_ref: str | None = "field_events_export.stub.csv",
) -> dict[str, Any]:
    return {
        "version": "0.4.5-phase5-field-loop",
        "status": "field_loop_scaffold_capture",
        "vetting_status": VETTING,
        "science_lock": SCIENCE_LOCK,
        "domains": ["fog_escarpment", "najd_arid"],
        "never_mix_domains": True,
        "allowed_species_ids": list(ALLOWED_SPECIES),
        "visit_types": list(VISIT_WINDOWS.keys()),
        "seeding_events_ref": events_ref,
        "field_observations_ref": observations_ref,
        "csv_export_stub_ref": csv_ref,
        "forbidden": list(FORBIDDEN),
        "ui_gates": {
            "partner_field_ui": False,
            "mountain_partner_ui": False,
            "writes_to_app_public": False,
            "auto_rewrite_scores": False,
            "published_rates": False,
            "partner_photo_gallery": False,
        },
        "ui_disclaimer": {"en": DISCLAIMER_EN, "ar": DISCLAIMER_AR},
        "mountain_ui": "hold",
        "phase6_later": False,
    }


def build_run_meta(
    *,
    n_events: int,
    n_observations: int,
    event_ids: list[str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "science_lock": SCIENCE_LOCK,
        "phase4_species_lock": "SCIENCE_LOCKS_v0.4_phase4_species",
        "vetting_status": VETTING,
        "status": "field_loop_scaffold_capture",
        "domains": ["fog_escarpment", "najd_arid"],
        "never_mix_domains": True,
        "mountain_ui": "hold",
        "campaign_numbers": False,
        "published_rates": False,
        "auto_rewrite_scores": False,
        "writes_to_app_public": False,
        "partner_field_ui": False,
        "n_events": n_events,
        "n_observations": n_observations,
        "event_ids": event_ids,
        "engines": ["engines/field_loop.py"],
        "runner": "run_field_loop.py",
        "artifact_files": [
            "seeding_events.sample.json",
            "field_observations.sample.json",
            "survival_observations.sample.json",
            "field_loop.json",
            "field_events_export.stub.csv",
            "run_meta.json",
        ],
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
        "agrofostery_lock_tip": (
            "Replace enums / reject rules from docs/phase5_field_loop_scaffold.json "
            "when mid-flight Agrofostery addenda land — keep validate_seeding_event "
            "and create_planned_followups as tip-update points."
        ),
    }


def sample_seeding_events() -> list[dict[str, Any]]:
    """1–2 Najd AOU + optional offline mountain cell labeled Hold. No fake survival."""
    return [
        {
            "event_id": "SE-2026-000001",
            "site_ref": "AOU-NJ-000001",
            "domain": "najd_arid",
            "species_id": "sp-najd-zsc",
            "event_date": "2026-01-15",
            "gps": {"lat": 17.12, "lon": 54.05, "accuracy_m": 8.0},
            "intervention_type": "seeding",
            "establishment_mode": "seed",
            "method": "pit",
            "timing_window": "winter_spring_rain",
            "provenance_class": "regional_dhofar",
            "seed_lot_id": None,
            "quantity": {
                "amount": 120,
                "unit": "seeds",
                "source": "operator_reported_unvalidated",
            },
            "operator_name": "najd_field_team_a",
            "organization": "baladiya",
            "n_participants": 4,
            "photos_event": [],
            "notes": "Scaffold sample — operator-confirmed pit seeding of سدر.",
            "override_note": None,
            "event_status": "logged",
            "linked_recommendation_id": None,
            "baseline_missing": True,
            "vetting_status": VETTING,
            "honesty_note_en": DISCLAIMER_EN,
            "honesty_note_ar": DISCLAIMER_AR,
        },
        {
            "event_id": "SE-2026-000002",
            "site_ref": "AOU-NJ-000003",
            "domain": "najd_arid",
            "species_id": "sp-najd-vtor",
            "event_date": "2026-02-01",
            "gps": {"lat": 17.18, "lon": 54.11, "accuracy_m": 12.0},
            "intervention_type": "planting",
            "establishment_mode": "vegetative_preferred",
            "method": "seedling",
            "timing_window": "irrigated",
            "provenance_class": "unknown",
            "seed_lot_id": None,
            "quantity": {
                "amount": 25,
                "unit": "seedlings",
                "source": "operator_reported_unvalidated",
            },
            "operator_name": "najd_field_team_b",
            "organization": "volunteers",
            "n_participants": 6,
            "photos_event": [
                {
                    "ref": "stubs/photos/SE-2026-000002/plot_pre.jpg",
                    "taken_at": "2026-02-01",
                    "caption": "Plot pre-plant — soil only",
                    "pii_flag": "none",
                }
            ],
            "notes": (
                "Scaffold sample — seedling planting of سمر. "
                "d30_germination is not_applicable (already a plant)."
            ),
            "override_note": None,
            "event_status": "logged",
            "linked_recommendation_id": None,
            "baseline_missing": True,
            "vetting_status": VETTING,
            "honesty_note_en": DISCLAIMER_EN,
            "honesty_note_ar": DISCLAIMER_AR,
        },
        {
            "event_id": "SE-2026-000003",
            "site_ref": "MPI-SAMPLE-000",
            "domain": "fog_escarpment",
            "species_id": "sp-fog-tdhof",
            "event_date": "2025-09-20",
            "gps": {"lat": 17.05, "lon": 54.45, "accuracy_m": 15.0},
            "intervention_type": "protect_regeneration",
            "establishment_mode": "protect_regeneration",
            "method": "protection_only",
            "timing_window": "early_post_khareef",
            "provenance_class": "local_same_jabal",
            "seed_lot_id": None,
            "quantity": None,
            "operator_name": "fog_offline_hold_team",
            "organization": "other",
            "n_participants": 2,
            "photos_event": [],
            "notes": (
                "OFFLINE mountain cell sample — Mountain partner UI Hold. "
                "Protect regeneration of ميست; germination not_applicable."
            ),
            "override_note": None,
            "khareef_stage": "early_post_khareef",
            "event_status": "logged",
            "linked_recommendation_id": None,
            "baseline_missing": True,
            "mountain_ui": "hold",
            "vetting_status": VETTING,
            "honesty_note_en": DISCLAIMER_EN,
            "honesty_note_ar": DISCLAIMER_AR,
        },
    ]


def events_to_csv_rows(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    """CSV export stub for field teams — no campaign planner columns as official."""
    rows = []
    for e in events:
        qty = e.get("quantity") or {}
        gps = e.get("gps") or {}
        rows.append(
            {
                "event_id": e["event_id"],
                "site_ref": e["site_ref"],
                "domain": e["domain"],
                "species_id": e["species_id"],
                "event_date": e["event_date"],
                "lat": str(gps.get("lat", "")),
                "lon": str(gps.get("lon", "")),
                "intervention_type": e["intervention_type"],
                "establishment_mode": e["establishment_mode"],
                "method": e["method"],
                "timing_window": e["timing_window"],
                "provenance_class": e["provenance_class"],
                "operator_name": e["operator_name"],
                "event_status": e["event_status"],
                "quantity_amount": "" if not qty else str(qty.get("amount", "")),
                "quantity_unit": "" if not qty else str(qty.get("unit", "")),
                "quantity_source": "" if not qty else str(qty.get("source", "")),
                "vetting_status": e["vetting_status"],
                "mountain_ui": e.get("mountain_ui", ""),
                "campaign_ha": "",
                "seed_kg": "",
                "crew_days": "",
                "note": "operator_reported_unvalidated only — not official campaign numbers",
            }
        )
    return rows
