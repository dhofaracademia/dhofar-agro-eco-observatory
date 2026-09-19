#!/usr/bin/env python3
"""
run_khareef_status.py — Khareef Status Tracker (Samhan → Sarfait), fog_escarpment only.

Binding: docs/SCIENCE_LOCKS_v0.4_khareef_status_tracker.md
Product: 3.A corridor status indicators — NOT a seeding map. 3.B Hold unchanged.

Artifacts under satellite/pipeline/artifacts/khareef_status/ (prefer khareef_status_cells.*).
Never mixes najd_arid. Never stamps post_khareef / post_khareef_mpi until
post window (default 2026-09-15–2026-10-31) + ≥1 SCL-clear S2 L2A + pipeline Approve.

USAGE:
  python satellite/pipeline/run_khareef_status.py --dry-run
  python satellite/pipeline/run_khareef_status.py
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parents[1]
DEFAULT_OUT = PIPELINE_DIR / "artifacts" / "khareef_status"
OUT_DIR = Path(os.environ.get("KHAREEF_STATUS_OUT", str(DEFAULT_OUT)))
MPI_META = (
    PIPELINE_DIR / "artifacts" / "mountain_pilot" / "mpi" / "mpi_run_meta.json"
)

DOMAIN = "fog_escarpment"
PRODUCT_STAMP = "provisional_satellite_analytical_service"
SCIENCE_LOCK = "SCIENCE_LOCKS_v0.4_khareef_status_tracker.md"
POST_WINDOW_START = date(2026, 9, 15)
POST_WINDOW_END = date(2026, 10, 31)

# Documented WGS84 bboxes [W, S, E, N] — seaward escarpment / monsoon woodland.
# Envelope ~ lon 53.0–55.0, lat 16.55–17.45. Exclude Najd leeward plateau.
SEGMENTS: dict[str, dict[str, Any]] = {
    "sarfait": {
        "bbox": [53.00, 16.65, 53.30, 16.95],
        "name_en": "Sarfait / western Qamar fog escarpment",
        "name_ar": "صرفيت / غرب القمر — منحدر الضباب",
        "optional": False,
        "centroid": [53.15, 16.80],
    },
    "qamar": {
        "bbox": [53.25, 16.70, 53.75, 17.05],
        "name_en": "Jabal Qamar seaward escarpment",
        "name_ar": "جبل القمر — المنحدر البحري",
        "optional": False,
        "centroid": [53.50, 16.88],
    },
    "qara": {
        "bbox": [54.05, 17.08, 54.22, 17.22],
        "name_en": "Jabal Qara fog-escarpment (locked mountain pilot bbox)",
        "name_ar": "جبل القرا — منحدر الضباب (مربع الطيار المقفول)",
        "optional": False,
        "centroid": [54.135, 17.15],
        "bbox_note": "Locked start bbox from mountain pilot — unchanged.",
    },
    "samhan": {
        "bbox": [54.55, 17.00, 54.95, 17.35],
        "name_en": "Jabal Samhan seaward escarpment",
        "name_ar": "جبل سمحان — المنحدر البحري",
        "optional": False,
        "centroid": [54.75, 17.18],
    },
    "mirbat_mughsayl": {
        "bbox": [54.35, 16.82, 54.70, 17.05],
        "name_en": "Mirbat–Mughsayl coastal fog fringe (catalog segment)",
        "name_ar": "مرباط–المغيسيل — هامش ضباب ساحلي (قطعة كتالوج)",
        "optional": True,
        "centroid": [54.52, 16.93],
    },
}

CORRIDOR_ORDER = ["samhan", "qara", "mirbat_mughsayl", "qamar", "sarfait"]  # east → west display
STAGE_ENUM = [
    "pre_khareef",
    "onset",
    "peak",
    "late_khareef",
    "post_khareef",
    "insufficient",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def asof_muscat() -> date:
    # Box is UTC; Asia/Muscat = UTC+4. Use env override for tests.
    override = os.environ.get("KHAREEF_STATUS_ASOF")
    if override:
        return date.fromisoformat(override)
    utc = datetime.now(timezone.utc)
    # Approximate Muscat local date without zoneinfo dependency
    from datetime import timedelta

    return (utc + timedelta(hours=4)).date()


def calendar_stage(asof: date) -> tuple[str, str]:
    """
    Calendar-heuristic stage label (not a phenology publication).
    Binding: never claim post_khareef before post window opens AND clear scene gate.
    Year-bound: windows use asof.year — Nov 1 is NEVER late_khareef
    (SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md §4).
    """
    # Rough Dhofar Khareef calendar (documented heuristic), always year-bound
    y = asof.year
    post_start = date(y, 9, 15)
    post_end = date(y, 10, 31)
    if asof < date(y, 6, 1):
        return "pre_khareef", "calendar_heuristic"
    if asof < date(y, 6, 21):
        return "onset", "calendar_heuristic"
    if asof < date(y, 8, 15):
        return "peak", "calendar_heuristic"
    if asof < post_start:
        return "late_khareef", "calendar_heuristic"
    # On/after post window start — still may not stamp post_khareef without EO gate
    if asof <= post_end:
        return "late_khareef", "calendar_heuristic_post_window_pending_clear_scene"
    # After post-window end (e.g. Nov 1+): never late_khareef
    return "insufficient", "calendar_heuristic"


def load_qara_mpi() -> dict[str, Any] | None:
    if not MPI_META.is_file():
        return None
    try:
        return json.loads(MPI_META.read_text())
    except json.JSONDecodeError:
        return None


def segment_status(
    segment_id: str,
    meta: dict[str, Any],
    asof: date,
    cal_stage: str,
    stage_method: str,
    qara_mpi: dict[str, Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Build per-segment honesty status. No fabricated NDVI/NDMI."""
    seg = SEGMENTS[segment_id]
    # Default fail-honest: no live STAC clear scenes claimed in this offline/dry path
    ndvi = None
    ndmi = None
    n_clear = 0
    data_quality = "insufficient_clear_scenes"
    product_kind = "insufficient"
    khareef_stage = "insufficient"
    evidence_level = "insufficient"
    scene_cite: dict[str, Any] | None = None
    mpi_note = None

    if segment_id == "qara" and qara_mpi:
        # Reuse existing mountain MPI onset evidence — honest product_kind
        pk = qara_mpi.get("product_kind") or "onset_window_dry_mpi_provisional"
        if pk == "post_khareef_mpi":
            # Safety: never inherit post stamp unless gate met (today it is not)
            pk = "onset_window_dry_mpi_provisional"
        product_kind = pk
        n_clear = int(qara_mpi.get("aoi_n_valid") or 0)
        data_quality = "onset_window_mpi_reuse"
        evidence_level = "satellite_onset_provisional"
        # Stage: calendar may say late_khareef; MPI evidence is onset-window — prefer
        # late_khareef OR insufficient, NEVER post_khareef before gate.
        if cal_stage == "post_khareef":
            khareef_stage = "late_khareef"
        elif cal_stage in STAGE_ENUM and cal_stage != "post_khareef":
            khareef_stage = cal_stage
        else:
            khareef_stage = "late_khareef"
        # NDMI from AOI curve not cell — leave null at cell; cite T0 scene if present
        t0d = qara_mpi.get("t0_diagnostics") or {}
        scene_cite = {
            "source": "Copernicus Sentinel-2 L2A via Microsoft Planetary Computer",
            "product_id": t0d.get("t0_product_id") or qara_mpi.get("t0_method"),
            "date": qara_mpi.get("t0_date"),
            "tile": None,
            "cloud_cover": None,
            "note": "Cited from mountain_pilot mpi_run_meta (onset T0); not a live peak/post claim.",
        }
        mpi_note = {
            "product_kind": product_kind,
            "t0_source_window": qara_mpi.get("t0_source_window"),
            "not_post_khareef_persistence": True,
            "aoi_mpi_class": qara_mpi.get("aoi_mpi_class"),
            "mpi_meta_path": str(MPI_META.relative_to(REPO_ROOT)),
        }
        ndmi = None  # no interpolated cell NDMI
        ndvi = None
    else:
        # No clear-scene claim for corridor expansion without STAC Approve
        khareef_stage = "insufficient"
        product_kind = "insufficient"
        evidence_level = "insufficient"
        data_quality = "no_scl_clear_claim_pending_stac"
        if dry_run:
            data_quality = "dry_run_insufficient"

    # Absolute gate: never post_khareef before window + clear + approve
    if khareef_stage == "post_khareef":
        khareef_stage = "late_khareef" if asof < POST_WINDOW_START else "insufficient"
    if product_kind == "post_khareef_mpi" and asof < POST_WINDOW_START:
        product_kind = "onset_window_dry_mpi_provisional"

    lon, lat = seg["centroid"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "id": f"KS-{segment_id}",
            "segment_id": segment_id,
            "name_en": seg["name_en"],
            "name_ar": seg["name_ar"],
            "domain": DOMAIN,
            "bbox": seg["bbox"],
            "optional_segment": bool(seg.get("optional")),
            "khareef_stage": khareef_stage,
            "stage_method": stage_method if segment_id == "qara" else "insufficient_pending_clear",
            "ndvi": ndvi,
            "ndmi": ndmi,
            "ndre": None,
            "ndre_available": False,
            "n_clear": n_clear,
            "data_quality": data_quality,
            "evidence_level": evidence_level,
            "product_kind": product_kind,
            "product_stamp": PRODUCT_STAMP,
            "partner_surface": "status_only",
            "seeding_recommendation": "hold",
            "suitability": None,
            "confidence": None,
            "action": None,
            "mpi": mpi_note,
            "scene_cite": scene_cite,
            "asof_date": asof.isoformat(),
            "why": [
                "Status cell only — vegetation/moisture indicators, not a plant-here site.",
                "Seeding-rec Hold (3.B) until post-khareef MPI window + pipeline Approve.",
                "Fog species catalog is list-only — not mixed onto this cell as a rec.",
            ],
        },
    }


def corridor_geojson(asof: date) -> dict[str, Any]:
    features = []
    for sid in ["sarfait", "qamar", "qara", "samhan", "mirbat_mughsayl"]:
        seg = SEGMENTS[sid]
        w, s, e, n = seg["bbox"]
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
                },
                "properties": {
                    "segment_id": sid,
                    "name_en": seg["name_en"],
                    "name_ar": seg["name_ar"],
                    "bbox": seg["bbox"],
                    "domain": DOMAIN,
                    "optional_segment": bool(seg.get("optional")),
                    "partner_surface": "status_only",
                    "seeding_recommendation": "hold",
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "name": "khareef_status_corridor_segments",
        "generated_at": utc_now(),
        "asof_date": asof.isoformat(),
        "domain": DOMAIN,
        "properties": {
            "partner_surface": "status_only",
            "seeding_recommendation": "hold",
            "product_stamp": PRODUCT_STAMP,
            "note_en": "Corridor segment envelopes Samhan→Sarfait (fog_escarpment). Not seeding polygons.",
            "note_ar": "مغلفات قطع الممر سمحان→صرفيت (منحدر الضباب). ليست مضلعات بذر.",
        },
        "features": features,
    }


def build(dry_run: bool = False) -> dict[str, Any]:
    asof = asof_muscat()
    cal_stage, stage_method = calendar_stage(asof)
    # Binding: today must not be post_khareef
    if asof < POST_WINDOW_START and cal_stage == "post_khareef":
        cal_stage = "late_khareef"
        stage_method = "calendar_heuristic_clamped_pre_post_window"

    qara_mpi = load_qara_mpi()
    cells = [
        segment_status(sid, SEGMENTS[sid], asof, cal_stage, stage_method, qara_mpi, dry_run)
        for sid in ["sarfait", "qamar", "qara", "samhan", "mirbat_mughsayl"]
    ]

    # Corridor-level stage for partner chip: never post_khareef pre-gate
    corridor_stage = cal_stage if cal_stage != "post_khareef" else "late_khareef"
    if all(c["properties"]["khareef_stage"] == "insufficient" for c in cells):
        corridor_stage = "insufficient"
    elif any(c["properties"]["segment_id"] == "qara" for c in cells):
        # Prefer qara calendar stage when we have onset MPI reuse + calendar late
        corridor_stage = next(
            c["properties"]["khareef_stage"] for c in cells if c["properties"]["segment_id"] == "qara"
        )

    # MPI product_kind honesty at corridor level
    corridor_pk = "insufficient"
    if qara_mpi:
        corridor_pk = qara_mpi.get("product_kind") or "onset_window_dry_mpi_provisional"
        if corridor_pk == "post_khareef_mpi" and asof < POST_WINDOW_START:
            corridor_pk = "onset_window_dry_mpi_provisional"

    cells_fc = {
        "type": "FeatureCollection",
        "name": "khareef_status_cells",
        "generated_at": utc_now(),
        "asof_date": asof.isoformat(),
        "domain": DOMAIN,
        "properties": {
            "note_en": "Khareef status — vegetation and moisture indicators. Not a seeding recommendation.",
            "note_ar": "حالة الخريف — مؤشرات غطاء ورطوبة. ليست توصية بذر.",
            "version": "0.4-status-1",
            "product_kind": corridor_pk,
            "product_stamp": PRODUCT_STAMP,
            "khareef_stage": corridor_stage,
            "stage_method": stage_method,
            "timing": "deferred",
            "seeding_recommendation": "hold",
            "partner_surface": "status_only",
            "mountain_3b_hold": True,
            "post_khareef_window": {
                "start": POST_WINDOW_START.isoformat(),
                "end": POST_WINDOW_END.isoformat(),
                "open_for_post_stamp": asof >= POST_WINDOW_START,
                "post_stamp_allowed": False,
                "reason": "Requires ≥1 SCL-clear S2 L2A in window + product_kind post_khareef_mpi + pipeline Approve SHA",
            },
            "science_lock": SCIENCE_LOCK,
            "forbidden": [
                "plant_here",
                "enrichment_seeding_scores",
                "onset_mpi_as_post_khareef",
                "mix_najd_arid",
                "experimental_seeding_toggle",
            ],
        },
        "features": cells,
    }

    segment_bboxes = {
        sid: {
            "bbox_wgs84_wsen": SEGMENTS[sid]["bbox"],
            "name_en": SEGMENTS[sid]["name_en"],
            "name_ar": SEGMENTS[sid]["name_ar"],
            "optional": bool(SEGMENTS[sid].get("optional")),
            **({"bbox_note": SEGMENTS[sid]["bbox_note"]} if SEGMENTS[sid].get("bbox_note") else {}),
        }
        for sid in SEGMENTS
    }

    run_meta = {
        "generated_at": utc_now(),
        "asof_date": asof.isoformat(),
        "timezone_note": "asof_date is Asia/Muscat calendar date",
        "status": "dry_run" if dry_run else "pilot_unverified",
        "layer": "khareef_status_tracker",
        "product": "khareef_status_tracker",
        "domain": DOMAIN,
        "provisional": True,
        "product_stamp": PRODUCT_STAMP,
        "product_kind": corridor_pk,
        "khareef_stage": corridor_stage,
        "stage_method": stage_method,
        "stage_enum": STAGE_ENUM,
        "not_post_khareef": corridor_stage != "post_khareef",
        "mountain_3b_hold": True,
        "lifts_3b": False,
        "partner_surface": "status_only",
        "seeding_recommendation": "hold",
        "corridor": {
            "name": "Samhan→Sarfait",
            "order_east_to_west": CORRIDOR_ORDER,
            "envelope_approx_wsen": [53.0, 16.55, 55.0, 17.45],
            "envelope_note": "Belt envelope only — per-segment bboxes are authoritative for PR glance",
        },
        "segment_bboxes": segment_bboxes,
        "allowed_indices": ["NDVI", "NDMI", "NDRE_optional", "true_color_cite", "MPI_stamped"],
        "mpi_reuse": {
            "qara_mpi_meta": str(MPI_META.relative_to(REPO_ROOT)) if qara_mpi else None,
            "qara_product_kind": (qara_mpi or {}).get("product_kind"),
            "qara_t0_source_window": (qara_mpi or {}).get("t0_source_window"),
            "not_post_khareef_persistence": True,
        },
        "post_khareef_gate": {
            "window_start": POST_WINDOW_START.isoformat(),
            "window_end": POST_WINDOW_END.isoformat(),
            "requires": [
                "ge1_clear_S2_L2A_SCL",
                "product_kind_post_khareef_or_insufficient",
                "pipeline_approve_sha",
            ],
            "post_stamp_allowed_today": False,
        },
        "honesty_en": "NDVI/NDMI are satellite proxies — not biomass t/ha, not soil moisture %. Stage is a label, not a phenology model publication. Insufficient when clear scenes missing.",
        "honesty_ar": "NDVI/NDMI مؤشرات قمرية — ليست كتلة حيوية ولا رطوبة تربة %. المرحلة تسمية وليست نموذج فينولوجيا منشور. غير كافٍ عند غياب المشاهد الصافية.",
        "partner_copy_en": "Khareef status — vegetation and moisture indicators. Not a seeding recommendation.",
        "partner_copy_ar": "حالة الخريف — مؤشرات غطاء ورطوبة. ليست توصية بذر.",
        "science_lock": SCIENCE_LOCK,
        "scaffold": "docs/phase_khareef_status_tracker_scaffold.json",
        "artifacts": {
            "run_meta": "satellite/pipeline/artifacts/khareef_status/run_meta.json",
            "khareef_status_cells": "satellite/pipeline/artifacts/khareef_status/khareef_status_cells.geojson",
            "corridor_segments": "satellite/pipeline/artifacts/khareef_status/corridor_segments.geojson",
        },
        "ui_wire": True,
        "app_public_mirror": "app/public/data/mountain/khareef_status_cells.geojson",
        "forbidden_partner_keys": [
            "campaign_ha",
            "seed_kg",
            "crew_days",
            "soil_moisture_pct",
            "germination_pct",
            "authority_approved",
            "experimental_seeding_toggle",
        ],
        "ai_pipeline_role": True,
        "human_review": "pending",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "run_meta.json", run_meta)
    write_json(OUT_DIR / "khareef_status_cells.geojson", cells_fc)
    write_json(OUT_DIR / "corridor_segments.geojson", corridor_geojson(asof))
    return run_meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Stamp status=dry_run; still write honest artifacts")
    args = ap.parse_args()
    meta = build(dry_run=args.dry_run)
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT_DIR),
                "asof_date": meta["asof_date"],
                "khareef_stage": meta["khareef_stage"],
                "product_kind": meta["product_kind"],
                "not_post_khareef": meta["not_post_khareef"],
                "segments": list(meta["segment_bboxes"].keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
