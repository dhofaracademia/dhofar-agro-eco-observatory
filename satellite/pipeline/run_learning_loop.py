#!/usr/bin/env python3
"""Regenerate Phase-6 Learning scaffold artifacts from SCIENCE_LOCKS.

Joins Decision/Seed ids to Field Loop SE-/FO- samples.
Writes pairs (eligible only), id-joins, frozen ledger, narrative report.
Does not write app/public/. Mountain UI Hold. No Learning UI.
Does not invent dated visits or outcome rates.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engines.learning_loop import (  # noqa: E402
    DISCLAIMER_EN,
    OUT_DIR,
    annual_report_csv_rows,
    annual_report_markdown,
    assert_no_rate_fields,
    build_annual_report,
    build_calibration_ledger,
    build_joins_document,
    build_learning_pair,
    build_model_improvement_log,
    build_run_meta,
    ineligible_reason,
    is_eligible,
    load_field_events,
    load_field_observations,
)


def _write_json(path: Path, doc: object) -> None:
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8"
    )



def _smoke_eligible_pair(events: list) -> None:
    """In-memory only — do not write a fabricated FO/LP into artifacts."""
    ev = events[0]
    dated = {
        "observation_id": "FO-2026-009999",
        "event_id": ev["event_id"],
        "visit_type": "d365_survival",
        "visit_date": "2027-01-20",
        "days_since_event": 370,
        "window_status": "on_window",
        "outcome_class": "present_target",
        "target_count": 2,
        "species_id_confidence": "probable",
    }
    if not is_eligible(dated, ev):
        raise SystemExit("smoke: dated on_window present_target must be eligible")
    pair = build_learning_pair(ev, dated, pair_seq=1, year=2026)
    if pair["pair_id"] != "LP-2026-000001":
        raise SystemExit("smoke: expected LP-2026-000001")
    assert_no_rate_fields(pair)
    na = dict(dated, visit_type="d30_germination", outcome_class="not_applicable")
    if ineligible_reason(na, ev) != "not_applicable":
        raise SystemExit("smoke: N/A germination must be excluded")
    missed = dict(dated, window_status="missed")
    if ineligible_reason(missed, ev) != "missed":
        raise SystemExit("smoke: missed must be excluded")
    undated = dict(dated, visit_date=None)
    if ineligible_reason(undated, ev) != "undated_stub":
        raise SystemExit("smoke: undated stub must be excluded")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    events = load_field_events()
    observations = load_field_observations()
    _smoke_eligible_pair(events)
    if not events:
        raise SystemExit("no Phase-5 seeding events found")

    joins = build_joins_document(events, observations)
    n_eligible = joins["n_eligible_pairs"]
    ledger = build_calibration_ledger(
        n_eligible_pairs=n_eligible, counts=joins["counts"]
    )
    report = build_annual_report(
        events,
        observations,
        joins["counts"],
        year=2026,
        sample_rows_not_a_season=True,
    )
    log = build_model_improvement_log(
        n_events=len(events),
        n_observations=len(observations),
        n_eligible_pairs=n_eligible,
    )
    meta = build_run_meta(
        n_events=len(events),
        n_observations=len(observations),
        n_eligible_pairs=n_eligible,
        event_ids=[e["event_id"] for e in events],
    )

    for doc in (joins, ledger, report, log, meta):
        assert_no_rate_fields(doc)

    if n_eligible != 0:
        raise SystemExit(
            "scaffold samples must yield 0 eligible pairs "
            f"(got {n_eligible}) — do not invent dated visits"
        )
    if any(p.get("eligible_for_calibration") for p in joins["pairs"]):
        raise SystemExit("unexpected eligible pair in scaffold sample")
    if ledger["calibration_status"] != "frozen_expert_v1":
        raise SystemExit("ledger must stay frozen_expert_v1")
    if ledger["auto_apply"] is not False:
        raise SystemExit("auto_apply must be false")
    if any(r.get("status") != "not_authorized" or r.get("delta") is not None for r in ledger["proposed_change"]):
        raise SystemExit("proposed_change must be not_authorized + delta null")

    _write_json(OUT_DIR / "prediction_field_joins.sample.json", joins)
    _write_json(OUT_DIR / "calibration_ledger.json", ledger)
    _write_json(OUT_DIR / "annual_report.template.json", report)
    _write_json(OUT_DIR / "model_improvement_log.json", log)
    _write_json(OUT_DIR / "run_meta.json", meta)

    md_path = OUT_DIR / "annual_report.export.stub.md"
    md_path.write_text(annual_report_markdown(report), encoding="utf-8")

    csv_path = OUT_DIR / "annual_report.export.stub.csv"
    rows = annual_report_csv_rows(report)
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    print("wrote", OUT_DIR)
    print("events", len(events), "observations", len(observations), "eligible_pairs", n_eligible)
    print("disclaimer:", DISCLAIMER_EN)


if __name__ == "__main__":
    main()
