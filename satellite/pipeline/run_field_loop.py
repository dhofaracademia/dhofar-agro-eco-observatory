#!/usr/bin/env python3
"""Regenerate Phase-5 Field Loop scaffold artifacts from SCIENCE_LOCKS.

Creates planned follow-ups from event_date. No fabricated survival/germination rates.
Does not write app/public/. Mountain UI Hold. No partner Field UI.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engines.field_loop import (  # noqa: E402
    DISCLAIMER_EN,
    OUT_DIR,
    build_field_loop_wrapper,
    build_run_meta,
    create_planned_followups,
    events_to_csv_rows,
    sample_seeding_events,
    validate_seeding_event,
)


def _write_json(path: Path, doc: object) -> None:
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    events = sample_seeding_events()
    for ev in events:
        bad = validate_seeding_event(ev)
        if bad:
            raise SystemExit(f"sample event rejected {ev['event_id']}: {bad}")

    observations: list[dict] = []
    seq = 1
    for ev in events:
        year = int(ev["event_id"].split("-")[1])
        batch = create_planned_followups(ev, obs_seq_start=seq, year=year)
        observations.extend(batch)
        seq += len(batch)

    events_doc = {
        "version": "0.4.5-phase5-field-loop",
        "science_lock": "SCIENCE_LOCKS_v0.4_phase5_field_loop",
        "vetting_status": "scientist_locked_pending_ea",
        "status": "scaffold_sample",
        "honesty_note_en": DISCLAIMER_EN,
        "events": events,
    }
    obs_doc = {
        "version": "0.4.5-phase5-field-loop",
        "science_lock": "SCIENCE_LOCKS_v0.4_phase5_field_loop",
        "vetting_status": "scientist_locked_pending_ea",
        "status": "scaffold_planned_followups",
        "note_en": (
            "Planned follow-up stubs only. outcome_class not_observed or "
            "not_applicable. No fabricated rates. Keep all real visits later; "
            "never overwrite. Alias file: survival_observations.sample.json"
        ),
        "honesty_note_en": DISCLAIMER_EN,
        "observations": observations,
    }

    _write_json(OUT_DIR / "seeding_events.sample.json", events_doc)
    _write_json(OUT_DIR / "field_observations.sample.json", obs_doc)
    # AgriTech-aligned alias filename (same payload; science IDs FO-/SE-)
    _write_json(OUT_DIR / "survival_observations.sample.json", obs_doc)
    _write_json(OUT_DIR / "field_loop.json", build_field_loop_wrapper())

    csv_path = OUT_DIR / "field_events_export.stub.csv"
    rows = events_to_csv_rows(events)
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    meta = build_run_meta(
        n_events=len(events),
        n_observations=len(observations),
        event_ids=[e["event_id"] for e in events],
    )
    _write_json(OUT_DIR / "run_meta.json", meta)

    print("wrote", OUT_DIR)
    print("events", len(events), "observations", len(observations))
    print("disclaimer:", DISCLAIMER_EN)


if __name__ == "__main__":
    main()
