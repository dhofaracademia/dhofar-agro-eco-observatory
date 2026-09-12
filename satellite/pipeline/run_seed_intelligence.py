#!/usr/bin/env python3
"""Phase-4 Seed Intelligence scaffolds — offline artifacts only.

Reads:
  - app/public/data/aou/aou_registry.json (Najd AOU site_refs)
  - satellite/pipeline/artifacts/mountain_pilot/mpi/mpi_cells.sample.geojson
    (restoration_mountain sample cells — offline notes only)

Writes under satellite/pipeline/artifacts/seed/:
  - species_catalog.json
  - site_species_matrix.json
  - seed_intelligence.json (wrapper)
  - seeding_protocol.stubs.json
  - run_meta.json

NEVER writes into app/public/.
NO Analysis / Restoration / Map Seed UI.
NO mountain partner UI / NO Decision→species wire in partner UI.
NO campaign_ha / seed_kg / crew_days official numbers.
Domains NEVER mixed: agriculture_aou vs restoration_mountain.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AOU_DIR = ROOT / "app" / "public" / "data" / "aou"
MPI_SAMPLE = (
    Path(__file__).resolve().parent
    / "artifacts"
    / "mountain_pilot"
    / "mpi"
    / "mpi_cells.sample.geojson"
)
OUT_DIR = Path(__file__).resolve().parent / "artifacts" / "seed"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engines.seed_intelligence import (  # noqa: E402
    DOMAIN_AGRICULTURE,
    DOMAIN_MOUNTAIN,
    STATUS_UNVALIDATED,
    SCIENCE_LOCK,
    AUTHORITY_SOURCE,
    FORBIDDEN,
    build_species_catalog,
    build_agriculture_rows,
    build_mountain_rows,
    build_site_species_matrix,
    build_seed_intelligence_wrapper,
    PROTOCOL_STEPS,
    PROTOCOL_LABELS,
)


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _aou_ids(registry: dict) -> list[str]:
    ids = []
    for u in registry.get("units") or []:
        aid = u.get("aou_id")
        if aid:
            ids.append(aid)
    return sorted(set(ids))


def _mountain_sample_site_refs(geojson: dict) -> list[str]:
    """Stable offline sample site_refs — not partner planting IDs."""
    refs: list[str] = []
    for i, feat in enumerate(geojson.get("features") or []):
        props = feat.get("properties") or {}
        # Prefer fog-belt / high sample strata when flagged; still include all
        # sample cells as offline scaffold sites (unvalidated).
        stratum = props.get("sample_stratum") or "sample"
        elev = props.get("elevation_m")
        elev_tag = f"{int(elev)}" if isinstance(elev, (int, float)) else "na"
        refs.append(f"MPI-SAMPLE-{i:03d}-{stratum}-{elev_tag}m")
    return refs


def main() -> int:
    registry_path = AOU_DIR / "aou_registry.json"
    if not registry_path.exists():
        print(f"ERROR: missing AOU registry at {registry_path}", file=sys.stderr)
        return 1
    if not MPI_SAMPLE.exists():
        print(f"ERROR: missing MPI sample at {MPI_SAMPLE}", file=sys.stderr)
        return 1

    registry = _load_json(registry_path)
    mpi = _load_json(MPI_SAMPLE)
    aou_ids = _aou_ids(registry)
    mountain_refs = _mountain_sample_site_refs(mpi)

    catalog = build_species_catalog()
    ag_rows = build_agriculture_rows(catalog, aou_ids)
    mt_rows = build_mountain_rows(catalog, mountain_refs)
    # Separate lists concatenated — never a shared recommend path
    matrix = build_site_species_matrix(ag_rows + mt_rows)
    wrapper = build_seed_intelligence_wrapper()

    protocol_stubs = {
        "schema_ref": "docs/spec_0.4/seed_intelligence.schema.json",
        "science_lock": SCIENCE_LOCK,
        "status": STATUS_UNVALIDATED,
        "mode": "manual_operator_confirmed",
        "auto_assign": False,
        "steps_enum": list(PROTOCOL_STEPS),
        "labels": PROTOCOL_LABELS,
        "forbidden": list(FORBIDDEN),
        "note_en": "Seeding protocol = manual / operator-confirmed only. No auto campaign planner.",
        "note_ar": "بروتوكول البذر يدوي / باعتماد المشغّل فقط. بلا مخطّط حملة تلقائي.",
    }

    run_meta = {
        "version": "0.4.4-phase4-seed-scaffold",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formula_ref": SCIENCE_LOCK,
        "status": STATUS_UNVALIDATED,
        "authority_source": AUTHORITY_SOURCE,
        "domains": [DOMAIN_AGRICULTURE, DOMAIN_MOUNTAIN],
        "never_mix_domains": True,
        "suitability_neq_confidence": True,
        "writes_to_app_public": False,
        "mountain_partner_ui": False,
        "link_mountain_decision_to_species_candidates": False,
        "analysis_seed_ui": False,
        "restoration_seed_ui": False,
        "campaign_quantity_fields": False,
        "forbidden": list(FORBIDDEN),
        "input_refs": {
            "aou_registry": "app/public/data/aou/aou_registry.json",
            "mpi_cells_sample": (
                "satellite/pipeline/artifacts/mountain_pilot/mpi/mpi_cells.sample.geojson"
            ),
        },
        "counts": {
            "aou_sites": len(aou_ids),
            "mountain_sample_sites": len(mountain_refs),
            "species_catalog": len(catalog["species"]),
            "matrix_rows_agriculture_aou": len(ag_rows),
            "matrix_rows_restoration_mountain": len(mt_rows),
            "matrix_rows_total": len(matrix["rows"]),
        },
        "artifact_files": [
            "species_catalog.json",
            "site_species_matrix.json",
            "seed_intelligence.json",
            "seeding_protocol.stubs.json",
            "run_meta.json",
        ],
        "engines": ["engines/seed_intelligence.py"],
        "runner": "run_seed_intelligence.py",
        "honesty_en": (
            "Offline Seed Intelligence scaffold. Domains never mixed. "
            "Scores unvalidated / null. No campaign ha/kg/crew. "
            "No Analysis/Restoration Seed UI. No mountain partner UI. "
            "Contact Agrofostery Authority before campaigns."
        ),
        "ui_gate": "Seed / Restoration / mountain partner UI deferred — artifacts-first PR",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "species_catalog.json", catalog)
    _write_json(OUT_DIR / "site_species_matrix.json", matrix)
    _write_json(OUT_DIR / "seed_intelligence.json", wrapper)
    _write_json(OUT_DIR / "seeding_protocol.stubs.json", protocol_stubs)
    _write_json(OUT_DIR / "run_meta.json", run_meta)

    # Sanity prints
    print(f"Wrote Seed Intelligence artifacts → {OUT_DIR}")
    print(
        f"  agriculture_aou rows={len(ag_rows)} "
        f"restoration_mountain rows={len(mt_rows)} "
        f"species={len(catalog['species'])}"
    )
    # Ensure no official campaign fields slipped into matrix rows
    for r in matrix["rows"]:
        for banned in ("campaign_ha", "seed_kg", "crew_days"):
            if banned in r:
                print(f"ERROR: banned field {banned} in row {r['site_ref']}", file=sys.stderr)
                return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
