"""Phase-6 Learning Loop scaffold — SCIENCE_LOCKS_v0.4_phase6_learning.

Join only. Counts only. expert_v1 weights frozen.
No published %; no auto species/site failed; no live weight writes.
Domains never mix. Phase-4 six only. Mountain UI Hold. No Learning UI.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIR.parents[1]
SCAFFOLD_PATH = REPO_ROOT / "docs" / "phase6_learning_scaffold.json"
PHASE4_SCAFFOLD = REPO_ROOT / "docs" / "phase4_species_scaffold.json"
FIELD_DIR = PIPELINE_DIR / "artifacts" / "field"
SEED_DIR = PIPELINE_DIR / "artifacts" / "seed"
DECISION_DIR = PIPELINE_DIR / "artifacts" / "decision"
OUT_DIR = PIPELINE_DIR / "artifacts" / "learning"

SCIENCE_LOCK = "SCIENCE_LOCKS_v0.4_phase6_learning"
VETTING = "scientist_locked_pending_ea"
VERSION = "0.4.6-phase6-learning"
CALIBRATION_STATUS = "frozen_expert_v1"
N_ELIGIBLE_UNLOCK = 20

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

HORIZONS = (
    "d30_germination",
    "d90_survival",
    "d180_establishment",
    "d365_survival",
)

ELIGIBLE_WINDOWS = frozenset({"on_window", "late"})
ELIGIBLE_OUTCOMES = frozenset(
    {
        "present_target",
        "none_detected",
        "dead_or_missing",
        "present_uncertain_id",
    }
)

FROZEN_ENGINES = (
    "ag_probability",
    "water_vigor_stress",
    "mpi",
    "aou_suitability_confidence",
    "site_x_species",
)

LEDGER_TARGETS = (
    ("ag_probability", "ag_probability_weights"),
    ("aou_suitability_confidence", "suitability_weights"),
    ("aou_suitability_confidence", "confidence_weights"),
    ("site_x_species", "species_matrix_cell"),
)

SPEC14_METRICS = (
    "Accuracy",
    "Precision",
    "Recall",
    "False Alert Rate",
    "Recommendation Success Rate",
    "Germination Accuracy",
    "Survival Prediction Accuracy",
)

COUNT_KEYS = (
    "n_events",
    "n_eligible_pairs",
    "n_present_target",
    "n_none_detected",
    "n_dead_or_missing",
    "n_uncertain",
    "n_missed_windows",
    "n_not_applicable",
)

FORBIDDEN_RATE_KEYS = (
    "germination_pct",
    "survival_pct",
    "germination_pct_operational",
    "survival_pct_operational",
    "recommendation_success",
    "accuracy",
    "count_ratio_unvalidated",
)

DISCLAIMER_EN = (
    "Learning scaffold — joins and counts only. "
    "Not a published success rate, not an Environment Authority approval. "
    "Weights remain frozen expert_v1."
)
DISCLAIMER_AR = (
    "مسودة تعلّم — ربط وعدّ فقط. "
    "ليست نسبة نجاح منشورة وليست اعتماداً من هيئة البيئة. "
    "الأوزان تبقى expert_v1 مجمّدة."
)

FORBIDDEN = [
    "species_failed_auto",
    "site_failed_auto",
    "rewrite_suitability_from_sparse_plots",
    "mountain_partner_ui",
    "partner_learning_dashboard",
    "fill_spec14_metrics",
    "germination_pct_operational",
    "survival_pct_operational",
    "recommendation_success",
    "missed_as_zero",
    "na_as_fail",
    "mix_domains_in_one_pool",
    "backfill_prediction",
    "live_weight_write",
    "auto_apply",
    "ml",
    "campaign_numbers",
    "Authority-approved",
    "معتمد من الهيئة",
]


def load_scaffold() -> dict[str, Any]:
    """Tip-update point — mid-flight Agrofostery addenda land here."""
    if SCAFFOLD_PATH.exists():
        return json.loads(SCAFFOLD_PATH.read_text(encoding="utf-8"))
    return {
        "lock_id": SCIENCE_LOCK,
        "calibration_status": CALIBRATION_STATUS,
        "proposed_change_status": "not_authorized",
        "proposed_change_delta": None,
        "future_unlock_not_this_pr": {
            "n_eligible_min": N_ELIGIBLE_UNLOCK,
            "first_horizon": "d365_survival",
        },
    }


def load_species_domain_map() -> dict[str, str]:
    """Tip-update: prefer Phase-4 scaffold if present."""
    if PHASE4_SCAFFOLD.exists():
        doc = json.loads(PHASE4_SCAFFOLD.read_text(encoding="utf-8"))
        out: dict[str, str] = {}
        for s in doc.get("species", []):
            if s.get("scaffold_include") and s.get("species_id") and s.get("domain"):
                out[s["species_id"]] = s["domain"]
        if out:
            return out
    return dict(SPECIES_DOMAIN)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_field_events() -> list[dict[str, Any]]:
    doc = load_json(FIELD_DIR / "seeding_events.sample.json")
    return list(doc.get("events") or [])


def load_field_observations() -> list[dict[str, Any]]:
    doc = load_json(FIELD_DIR / "field_observations.sample.json")
    return list(doc.get("observations") or [])


def aou_id_from_site(site_ref: str | None) -> str | None:
    if site_ref and str(site_ref).startswith("AOU-"):
        return site_ref
    return None


def ineligible_reason(
    observation: dict[str, Any], event: dict[str, Any] | None = None
) -> str | None:
    """Return None if eligible, else a locked reason string.

    Eligible = dated visit + window_status on_window|late
    + outcome in {present_target, none_detected, dead_or_missing, present_uncertain_id}.
    Exclude missed / not_observed / early / undated stub / not_applicable.
    """
    visit_type = observation.get("visit_type")
    if visit_type not in HORIZONS:
        return "not_a_learning_horizon"
    if event is not None:
        if observation.get("event_id") != event.get("event_id"):
            return "event_id_mismatch"
        domain_map = load_species_domain_map()
        sid = event.get("species_id")
        expected = domain_map.get(sid) or SPECIES_DOMAIN.get(sid)
        if expected and event.get("domain") != expected:
            return "domain_ne_species_domain"
        if sid not in ALLOWED_SPECIES and sid not in domain_map:
            return "species_id_not_in_six"
    if not observation.get("visit_date"):
        return "undated_stub"
    window = observation.get("window_status")
    if window == "missed":
        return "missed"
    if window == "early":
        return "early"
    if window not in ELIGIBLE_WINDOWS:
        return "window_status_%s" % window
    outcome = observation.get("outcome_class")
    if outcome == "not_observed":
        return "not_observed"
    if outcome == "not_applicable":
        return "not_applicable"
    if outcome not in ELIGIBLE_OUTCOMES:
        return "outcome_%s" % outcome
    return None


def is_eligible(
    observation: dict[str, Any], event: dict[str, Any] | None = None
) -> bool:
    return ineligible_reason(observation, event) is None


def prediction_snapshot(event: dict[str, Any]) -> dict[str, Any]:
    """What we thought at event time. Never back-fill suitability after the visit."""
    return {
        "linked_recommendation_id": event.get("linked_recommendation_id"),
        "suitability_stub": None,
        "suitability_status": "none",
        "timing_window": event.get("timing_window"),
        "intervention_type": event.get("intervention_type"),
        "establishment_mode": event.get("establishment_mode"),
        "provenance_class": event.get("provenance_class"),
    }


def actual_from_observation(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "visit_type": observation.get("visit_type"),
        "visit_date": observation.get("visit_date"),
        "days_since_event": observation.get("days_since_event"),
        "window_status": observation.get("window_status"),
        "outcome_class": observation.get("outcome_class"),
        "target_count": observation.get("target_count"),
        "species_id_confidence": observation.get("species_id_confidence"),
    }


def assert_no_rate_fields(doc: Any, path: str = "$") -> None:
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k in FORBIDDEN_RATE_KEYS:
                raise ValueError("forbidden rate field %s at %s" % (k, path))
            assert_no_rate_fields(v, "%s.%s" % (path, k))
    elif isinstance(doc, list):
        for i, item in enumerate(doc):
            assert_no_rate_fields(item, "%s[%d]" % (path, i))


def build_learning_pair(
    event: dict[str, Any],
    observation: dict[str, Any],
    *,
    pair_seq: int,
    year: int,
) -> dict[str, Any]:
    """Mint LP-{YYYY}-{NNNNNN} for one SE x one eligible FO at one horizon."""
    reason = ineligible_reason(observation, event)
    if reason:
        raise ValueError(
            "refusing ineligible pair %s/%s: %s"
            % (event.get("event_id"), observation.get("observation_id"), reason)
        )
    return {
        "pair_id": "LP-%d-%06d" % (year, pair_seq),
        "event_id": event["event_id"],
        "observation_id": observation["observation_id"],
        "horizon": observation["visit_type"],
        "domain": event["domain"],
        "species_id": event["species_id"],
        "site_ref": event.get("site_ref"),
        "aou_id": aou_id_from_site(event.get("site_ref")),
        "prediction": prediction_snapshot(event),
        "actual": actual_from_observation(observation),
        "eligible_for_calibration": True,
        "vetting_status": VETTING,
        "stamp": ["experimental", "unvalidated"],
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
    }


def build_id_join(event: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """Id-only SE <-> FO <-> site_ref <-> recommendation link. Not a LearningPair."""
    reason = ineligible_reason(observation, event)
    return {
        "event_id": event["event_id"],
        "observation_id": observation["observation_id"],
        "site_ref": event.get("site_ref"),
        "aou_id": aou_id_from_site(event.get("site_ref")),
        "linked_recommendation_id": event.get("linked_recommendation_id"),
        "domain": event.get("domain"),
        "species_id": event.get("species_id"),
        "horizon": observation.get("visit_type"),
        "window_status": observation.get("window_status"),
        "outcome_class": observation.get("outcome_class"),
        "visit_date": observation.get("visit_date"),
        "eligible_for_calibration": reason is None,
        "ineligible_reason": reason,
        "pair_id": None,
    }


def empty_counts(
    *,
    horizon: str | None,
    domain: str | None,
    species_id: str | None,
    calibration_pool: bool,
) -> dict[str, Any]:
    return {
        "group": {
            "horizon": horizon,
            "domain": domain,
            "species_id": species_id,
        },
        "n_events": 0,
        "n_eligible_pairs": 0,
        "n_present_target": 0,
        "n_none_detected": 0,
        "n_dead_or_missing": 0,
        "n_uncertain": 0,
        "n_missed_windows": 0,
        "n_not_applicable": 0,
        "thin_n": True,
        "calibration_pool": calibration_pool,
    }


def _inc_outcome(row: dict[str, Any], outcome: str | None) -> None:
    if outcome == "present_target":
        row["n_present_target"] += 1
    elif outcome == "none_detected":
        row["n_none_detected"] += 1
    elif outcome == "dead_or_missing":
        row["n_dead_or_missing"] += 1
    elif outcome == "present_uncertain_id":
        row["n_uncertain"] += 1


def build_counts(
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Raw n only. Never emit percents. present_uncertain_id never pooled into present_target."""
    obs_by_event: dict[str, list[dict[str, Any]]] = {}
    for o in observations:
        obs_by_event.setdefault(o.get("event_id"), []).append(o)

    keys: dict[tuple, dict[str, Any]] = {}

    def bucket(horizon: str | None, domain: str | None, species_id: str | None) -> dict[str, Any]:
        k = (horizon, domain, species_id)
        if k not in keys:
            pool = domain is not None and horizon is not None and species_id is not None
            keys[k] = empty_counts(
                horizon=horizon,
                domain=domain,
                species_id=species_id,
                calibration_pool=pool,
            )
        return keys[k]

    events_seen: dict[tuple, set[str]] = {}

    def mark_event(horizon: str | None, domain: str | None, species_id: str | None, eid: str) -> None:
        k = (horizon, domain, species_id)
        events_seen.setdefault(k, set()).add(eid)

    for ev in events:
        eid = ev["event_id"]
        domain = ev.get("domain")
        sid = ev.get("species_id")
        mark_event(None, None, None, eid)
        mark_event(None, domain, None, eid)
        mark_event(None, domain, sid, eid)
        for o in obs_by_event.get(eid, []):
            h = o.get("visit_type")
            if h not in HORIZONS:
                continue
            mark_event(h, None, None, eid)
            mark_event(h, domain, None, eid)
            mark_event(h, domain, sid, eid)
            row_h = bucket(h, domain, sid)
            row_hd = bucket(h, domain, None)
            row_ho = bucket(h, None, None)
            row_d = bucket(None, domain, None)
            row_o = bucket(None, None, None)
            # Coverage from FO fields (not first ineligible reason).
            # Undated stubs still report missed / N/A from window_status / outcome_class.
            targets = (row_h, row_hd, row_ho, row_d, row_o)
            if o.get("outcome_class") == "not_applicable":
                for r in targets:
                    r["n_not_applicable"] += 1
            elif o.get("window_status") == "missed":
                for r in targets:
                    r["n_missed_windows"] += 1

    for k, eids in events_seen.items():
        bucket(*k)["n_events"] = len(eids)

    for p in pairs:
        h = p.get("horizon")
        domain = p.get("domain")
        sid = p.get("species_id")
        outcome = (p.get("actual") or {}).get("outcome_class")
        for row in (
            bucket(h, domain, sid),
            bucket(h, domain, None),
            bucket(h, None, None),
            bucket(None, domain, None),
            bucket(None, None, None),
        ):
            row["n_eligible_pairs"] += 1
            _inc_outcome(row, outcome)

    rows = list(keys.values())
    for row in rows:
        row["thin_n"] = row["n_eligible_pairs"] < N_ELIGIBLE_UNLOCK
        if row["group"]["domain"] is None:
            row["calibration_pool"] = False
            if row["group"]["horizon"] is None:
                row["note"] = "display_only_overall — not a fog+Najd calibration pool"
            else:
                row["note"] = "display_only — domains not pooled for calibration"
    rows.sort(
        key=lambda r: (
            r["group"]["horizon"] or "",
            r["group"]["domain"] or "",
            r["group"]["species_id"] or "",
        )
    )
    return rows


def join_pairs(
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_event = {e["event_id"]: e for e in events}
    pairs: list[dict[str, Any]] = []
    id_joins: list[dict[str, Any]] = []
    seq = 1
    for obs in observations:
        ev = by_event.get(obs.get("event_id"))
        if ev is None:
            continue
        if obs.get("visit_type") not in HORIZONS:
            continue
        id_joins.append(build_id_join(ev, obs))
        if is_eligible(obs, ev):
            year = int(str(obs.get("observation_id") or ev["event_id"]).split("-")[1])
            pairs.append(build_learning_pair(ev, obs, pair_seq=seq, year=year))
            seq += 1
    return pairs, id_joins


def build_joins_document(
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    pairs, id_joins = join_pairs(events, observations)
    counts = build_counts(events, observations, pairs)
    n_eligible = sum(1 for j in id_joins if j["eligible_for_calibration"])
    doc = {
        "version": VERSION,
        "science_lock": SCIENCE_LOCK,
        "vetting_status": VETTING,
        "status": "learning_scaffold_join",
        "stamp": ["experimental", "unvalidated", "sample_rows_not_a_season"],
        "sample_rows_not_a_season": True,
        "domains": ["fog_escarpment", "najd_arid"],
        "never_mix_domains": True,
        "allowed_species_ids": list(ALLOWED_SPECIES),
        "horizons": list(HORIZONS),
        "field_events_ref": "artifacts/field/seeding_events.sample.json",
        "field_observations_ref": "artifacts/field/field_observations.sample.json",
        "seed_matrix_ref": "artifacts/seed/site_species_matrix.json",
        "decision_ref": "artifacts/decision/run_meta.json",
        "join_rule": "one SE x one eligible FO at one horizon; ids only; no back-fill",
        "n_events": len(events),
        "n_observations_scanned": len(observations),
        "n_id_joins": len(id_joins),
        "n_eligible_pairs": n_eligible,
        "pairs": pairs,
        "id_joins": id_joins,
        "counts": counts,
        "forbidden": list(FORBIDDEN),
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
        "ui_gates": {
            "partner_learning_dashboard": False,
            "mountain_partner_ui": False,
            "writes_to_app_public": False,
            "auto_rewrite_scores": False,
            "published_rates": False,
            "auto_apply": False,
        },
        "mountain_ui": "hold",
    }
    assert_no_rate_fields(doc)
    return doc


def build_calibration_ledger(
    *,
    n_eligible_pairs: int,
    counts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """proposed_change[] only not_authorized + delta null. auto_apply false."""
    scaffold = load_scaffold()
    future = scaffold.get("future_unlock_not_this_pr") or {
        "n_eligible_min": N_ELIGIBLE_UNLOCK,
        "group": "species_id x domain x horizon",
        "first_horizon": "d365_survival",
        "second_horizon": "d180_establishment",
        "no_unlock_from_d30_alone": True,
        "requires_scientist_signoff": True,
    }
    rows = []
    for i, (engine, target) in enumerate(LEDGER_TARGETS, start=1):
        rows.append(
            {
                "proposal_id": "CAL-2026-%06d" % i,
                "engine": engine,
                "target": target,
                "proposed_change": {},
                "delta": None,
                "evidence_n": n_eligible_pairs,
                "thin_n": n_eligible_pairs < N_ELIGIBLE_UNLOCK,
                "status": "not_authorized",
                "auto_apply": False,
                "requires": ["agrofostery_approve", "cos_gate"],
                "note_en": (
                    "Frozen expert_v1 — no live write this PR. "
                    "Future unlock (not this PR): n>=%d "
                    "per species x domain x horizon; d365 first."
                    % N_ELIGIBLE_UNLOCK
                ),
            }
        )
    doc = {
        "version": VERSION,
        "science_lock": SCIENCE_LOCK,
        "vetting_status": VETTING,
        "calibration_status": CALIBRATION_STATUS,
        "auto_apply": False,
        "live_weight_writes": False,
        "mix_domains_in_one_pool": False,
        "published_rates": False,
        "mountain_ui": "hold",
        "frozen_engines": list(FROZEN_ENGINES),
        "future_unlock_not_this_pr": future,
        "proposed_change": rows,
        "counts_ref": "prediction_field_joins.sample.json#counts",
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
        "forbidden": list(FORBIDDEN),
        "agrofostery_lock_tip": (
            "Replace proposed_change status/delta from "
            "docs/phase6_learning_scaffold.json when a later lock authorizes "
            "draft deltas — keep build_calibration_ledger as the tip-update point."
        ),
    }
    assert_no_rate_fields(doc)
    return doc


def _section(sid: str, title_en: str, title_ar: str, body_en: str, body_ar: str) -> dict[str, str]:
    return {
        "id": sid,
        "title_en": title_en,
        "title_ar": title_ar,
        "body_en": body_en,
        "body_ar": body_ar,
    }


def build_annual_report(
    events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    counts: list[dict[str, Any]],
    *,
    year: int = 2026,
    sample_rows_not_a_season: bool = True,
) -> dict[str, Any]:
    n_by_domain: dict[str, int] = {}
    n_by_species: dict[str, int] = {}
    n_by_intervention: dict[str, int] = {}
    for e in events:
        n_by_domain[e["domain"]] = n_by_domain.get(e["domain"], 0) + 1
        n_by_species[e["species_id"]] = n_by_species.get(e["species_id"], 0) + 1
        key = e["intervention_type"]
        n_by_intervention[key] = n_by_intervention.get(key, 0) + 1

    overall = next(
        (
            c
            for c in counts
            if c["group"]["horizon"] is None
            and c["group"]["domain"] is None
            and c["group"]["species_id"] is None
        ),
        empty_counts(horizon=None, domain=None, species_id=None, calibration_pool=False),
    )

    sections = [
        _section(
            "year_khareef",
            "Year + Khareef stage notes",
            "السنة وملاحظات مرحلة الخريف",
            "Narrative template for %d. No live onset claim. Khareef stage notes stay facts from field/event records only." % year,
            "قالب سردي لسنة %d. لا ادعاء لبداية خريف حيّ. ملاحظات المرحلة تبقى وقائع من السجلات فقط." % year,
        ),
        _section(
            "events_logged",
            "Events logged",
            "الأحداث المسجّلة",
            "n_events=%d by domain %s, species %s, intervention %s. Scaffold samples — not a field season."
            % (len(events), n_by_domain, n_by_species, n_by_intervention),
            "عدد الأحداث=%d. عينات سقالة — ليست موسماً ميدانياً." % len(events),
        ),
        _section(
            "visit_coverage",
            "Visit coverage",
            "تغطية الزيارات",
            "n_eligible_pairs=%d; n_missed_windows=%d; n_not_applicable=%d. missed/not_observed = coverage gap, not zero."
            % (overall["n_eligible_pairs"], overall["n_missed_windows"], overall["n_not_applicable"]),
            "أزواج مؤهلة=%d؛ نوافذ فائتة=%d؛ غير منطبق=%d. الفائت/غير المشاهد فجوة تغطية لا صفراً."
            % (overall["n_eligible_pairs"], overall["n_missed_windows"], overall["n_not_applicable"]),
        ),
        _section(
            "outcome_counts",
            "Outcome counts (no percents)",
            "عدّ النتائج (بلا نسب)",
            "n_present_target=%d; n_none_detected=%d; n_dead_or_missing=%d; n_uncertain=%d (never pooled into present_target). No germination_pct / survival_pct."
            % (overall["n_present_target"], overall["n_none_detected"], overall["n_dead_or_missing"], overall["n_uncertain"]),
            "حاضر مستهدف=%d؛ غير مكتشف=%d؛ ميت/مفقود=%d؛ غير مؤكد=%d. بلا نسب إنبات/بقاء."
            % (overall["n_present_target"], overall["n_none_detected"], overall["n_dead_or_missing"], overall["n_uncertain"]),
        ),
        _section(
            "qualitative_notes",
            "Qualitative notes",
            "ملاحظات نوعية",
            "Grazing / washout / drought / irrigation notes come from FO covariates only — none invented.",
            "ملاحظات الرعي/الجرف/الجفاف/الري من متغيرات الزيارة فقط — لا اختراع.",
        ),
        _section(
            "honesty",
            "Honesty box",
            "صندوق الأمانة",
            DISCLAIMER_EN + " Insufficient n. Weights frozen. Not EA approval.",
            DISCLAIMER_AR + " العدد غير كافٍ. الأوزان مجمّدة. ليست موافقة هيئة البيئة.",
        ),
        _section(
            "metrics_reserved",
            "Metrics reserved (Spec §14)",
            "مقاييس محجوزة (المواصفة §14)",
            "Accuracy / Precision / Recall / False Alert Rate / Recommendation Success Rate / Germination Accuracy / Survival Prediction Accuracy remain named, empty, forbidden to fill.",
            "الدقة والاستدعاء ومعدلات النجاح/الإنبات/البقاء تبقى أسماء فارغة ممنوعاً ملؤها.",
        ),
    ]

    metrics = [{"name": name, "value": None, "reason": "insufficient_n"} for name in SPEC14_METRICS]

    doc = {
        "version": VERSION,
        "science_lock": SCIENCE_LOCK,
        "vetting_status": VETTING,
        "year": year,
        "stamp": "narrative_template_only",
        "unpublished_scaffold": True,
        "sample_rows_not_a_season": sample_rows_not_a_season,
        "mountain_ui": "hold",
        "published_rates": False,
        "narrative_sections": sections,
        "tables": {
            "events_logged": {
                "n_events": len(events),
                "by_domain": n_by_domain,
                "by_species": n_by_species,
                "by_intervention": n_by_intervention,
            },
            "visit_coverage": {
                "n_eligible_pairs": overall["n_eligible_pairs"],
                "n_missed_windows": overall["n_missed_windows"],
                "n_not_applicable": overall["n_not_applicable"],
            },
            "outcome_class_counts": {
                "n_present_target": overall["n_present_target"],
                "n_none_detected": overall["n_none_detected"],
                "n_dead_or_missing": overall["n_dead_or_missing"],
                "n_uncertain": overall["n_uncertain"],
            },
            "counts": counts,
        },
        "metrics_reserved": metrics,
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
        "forbidden": list(FORBIDDEN),
    }
    assert_no_rate_fields(doc)
    return doc


def annual_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Annual restoration report (scaffold) — %s" % report["year"],
        "",
        "**Stamp:** `%s` · unpublished_scaffold=%s · sample_rows_not_a_season=%s"
        % (report["stamp"], report["unpublished_scaffold"], report["sample_rows_not_a_season"]),
        "",
        "**EN:** %s" % report["honesty_note_en"],
        "**AR:** %s" % report["honesty_note_ar"],
        "",
        "No germination_pct / survival_pct / recommendation_success. Counts only.",
        "",
    ]
    for sec in report["narrative_sections"]:
        lines.append("## %s" % sec["title_en"])
        lines.append("### %s" % sec["title_ar"])
        lines.append("")
        lines.append(sec["body_en"])
        lines.append("")
        lines.append(sec["body_ar"])
        lines.append("")
    tables = report["tables"]
    lines.append("## Tables (raw counts)")
    lines.append("")
    lines.append(
        "| group | n_events | n_eligible_pairs | n_present_target | n_none_detected | n_dead_or_missing | n_uncertain | n_missed_windows | n_not_applicable |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c in tables.get("counts") or []:
        g = c["group"]
        label = "/".join(x or "*" for x in (g.get("horizon"), g.get("domain"), g.get("species_id")))
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                label,
                c["n_events"],
                c["n_eligible_pairs"],
                c["n_present_target"],
                c["n_none_detected"],
                c["n_dead_or_missing"],
                c["n_uncertain"],
                c["n_missed_windows"],
                c["n_not_applicable"],
            )
        )
    lines.append("")
    lines.append("## Metrics reserved (all null)")
    lines.append("")
    for m in report["metrics_reserved"]:
        lines.append("- %s: `null` (%s)" % (m["name"], m["reason"]))
    lines.append("")
    return "\n".join(lines)


def annual_report_csv_rows(report: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for c in report["tables"].get("counts") or []:
        g = c["group"]
        rows.append(
            {
                "horizon": g.get("horizon") or "",
                "domain": g.get("domain") or "",
                "species_id": g.get("species_id") or "",
                "n_events": str(c["n_events"]),
                "n_eligible_pairs": str(c["n_eligible_pairs"]),
                "n_present_target": str(c["n_present_target"]),
                "n_none_detected": str(c["n_none_detected"]),
                "n_dead_or_missing": str(c["n_dead_or_missing"]),
                "n_uncertain": str(c["n_uncertain"]),
                "n_missed_windows": str(c["n_missed_windows"]),
                "n_not_applicable": str(c["n_not_applicable"]),
                "thin_n": str(c.get("thin_n")),
                "calibration_pool": str(c.get("calibration_pool")),
                "note": "outcome_class counts only — not official campaign numbers",
            }
        )
    return rows


def build_model_improvement_log(
    *,
    n_events: int,
    n_observations: int,
    n_eligible_pairs: int,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "science_lock": SCIENCE_LOCK,
        "vetting_status": VETTING,
        "note_en": (
            "Changelog of lock versions + dataset n. "
            "Not a promotion log — weights stay frozen_expert_v1."
        ),
        "entries": [
            {
                "lock_id": "SCIENCE_LOCKS_v0.4_phase4_species",
                "phase": 4,
                "dataset_n": {"species": 6},
                "note": "Scientist-locked six-species catalog",
            },
            {
                "lock_id": "SCIENCE_LOCKS_v0.4_phase5_field_loop",
                "phase": 5,
                "dataset_n": {"events": n_events, "observations": n_observations},
                "note": "Field Loop scaffold samples (undated FO stubs)",
            },
            {
                "lock_id": SCIENCE_LOCK,
                "phase": 6,
                "dataset_n": {
                    "events": n_events,
                    "observations": n_observations,
                    "eligible_pairs": n_eligible_pairs,
                },
                "calibration_status": CALIBRATION_STATUS,
                "note": "Learning scaffold — zero eligible pairs from Phase-5 stubs",
            },
        ],
    }


def build_run_meta(
    *,
    n_events: int,
    n_observations: int,
    n_eligible_pairs: int,
    event_ids: list[str],
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "science_lock": SCIENCE_LOCK,
        "phase4_species_lock": "SCIENCE_LOCKS_v0.4_phase4_species",
        "phase5_field_lock": "SCIENCE_LOCKS_v0.4_phase5_field_loop",
        "vetting_status": VETTING,
        "status": "learning_scaffold_join",
        "calibration_status": CALIBRATION_STATUS,
        "version": VERSION,
        "domains": ["fog_escarpment", "najd_arid"],
        "never_mix_domains": True,
        "mountain_ui": "hold",
        "campaign_numbers": False,
        "published_rates": False,
        "auto_rewrite_scores": False,
        "auto_apply": False,
        "live_weight_writes": False,
        "writes_to_app_public": False,
        "partner_learning_dashboard": False,
        "n_events": n_events,
        "n_observations": n_observations,
        "n_eligible_pairs": n_eligible_pairs,
        "event_ids": event_ids,
        "engines": ["engines/learning_loop.py"],
        "runner": "run_learning_loop.py",
        "artifact_files": [
            "prediction_field_joins.sample.json",
            "calibration_ledger.json",
            "annual_report.template.json",
            "annual_report.export.stub.md",
            "annual_report.export.stub.csv",
            "model_improvement_log.json",
            "run_meta.json",
        ],
        "honesty_note_en": DISCLAIMER_EN,
        "honesty_note_ar": DISCLAIMER_AR,
        "agrofostery_lock_tip": (
            "Replace eligibility / ledger rules from "
            "docs/phase6_learning_scaffold.json when mid-flight Agrofostery "
            "addenda land — keep ineligible_reason, build_learning_pair, "
            "build_calibration_ledger, build_annual_report as tip-update points."
        ),
    }
