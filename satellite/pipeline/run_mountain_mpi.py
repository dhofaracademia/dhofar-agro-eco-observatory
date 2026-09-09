#!/usr/bin/env python3
"""
run_mountain_mpi.py — Phase-2 OFFLINE Moisture Persistence (MPI) curve.

Binding: docs/SCIENCE_LOCKS_v0.4_phase1_2.md §5 MPI + §6 regen ladder stubs.

HARD UI GATE: writes ONLY under satellite/pipeline/artifacts/mountain_pilot/
(including mpi/). Never writes app/public/. No partner Map/Analysis/Restoration UI.

Builds on run_mountain_pilot.py DEM helpers (elev/slope/aspect/TWI) + SCL fail-honest NDMI.
Prefer onset + post-khareef; default post window late Sep–Oct (fixes prior Sep 1–8 cloud fail).

USAGE:
  python satellite/pipeline/run_mountain_mpi.py --dry-run
  python satellite/pipeline/run_mountain_mpi.py
  python satellite/pipeline/run_mountain_mpi.py --post-range 2026-09-15/2026-10-31
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parents[1]
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))
DEFAULT_OUT = PIPELINE_DIR / "artifacts" / "mountain_pilot"
OUT_DIR = Path(os.environ.get("MOUNTAIN_PILOT_OUT", str(DEFAULT_OUT)))
MPI_DIR = OUT_DIR / "mpi"

# Load sibling run_mountain_pilot as module (shared DEM / NDMI / bbox)
_spec = importlib.util.spec_from_file_location(
    "run_mountain_pilot", PIPELINE_DIR / "run_mountain_pilot.py"
)
assert _spec and _spec.loader
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)

from engines.mpi import (  # noqa: E402
    DEFAULT_DRY_BASELINE_NDMI,
    FORBIDDEN_PARTNER_KEYS,
    LAYER_MPI,
    MPI_LAGS_WEEKS,
    MPI_SEARCH_HALF_WINDOW_DAYS,
    STATUS_INSUFFICIENT,
    STATUS_PILOT,
    assert_no_forbidden_partner_keys,
    classify_mpi,
    date_window,
    regeneration_ladder_doc,
    stratified_sample_indices,
    utc_now_iso,
)

PILOT_BBOX = rp.PILOT_BBOX
BBOX_LOCK_NOTE = rp.BBOX_LOCK_NOTE
SOURCE_S2 = rp.SOURCE_S2
MIN_CLEAR_FRAC = rp.MIN_CLEAR_FRAC


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def _scene_date(item) -> date | None:
    if item.datetime is None:
        return None
    return item.datetime.date()


def list_s2_candidates(bbox: list[float], date_range: str, cloud_lt: float = 40.0) -> list:
    """STAC search sorted by cloud then date. Empty list on no hits — never fabricate."""
    catalog = rp.open_catalog()
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": cloud_lt}},
        max_items=80,
    )
    items = list(search.items())
    items.sort(
        key=lambda it: (
            it.properties.get("eo:cloud_cover", 100.0),
            _scene_date(it) or date.max,
        )
    )
    return items


def pick_t0(
    bbox: list[float],
    post_range: str,
    onset_range: str,
    cloud_lt: float,
) -> tuple[date | None, str, dict[str, Any]]:
    """
    Dynamic T0 per §5.1:
      Prefer first clear post-khareef (late Sep–Oct) scene;
      else first clear post-onset scene;
      else None (insufficient).
    Does NOT invent live Khareef onset detection — windows are documented search ranges.
    """
    diagnostics: dict[str, Any] = {
        "post_range_searched": post_range,
        "onset_range_searched": onset_range,
        "cloud_lt": cloud_lt,
    }

    post_items = list_s2_candidates(bbox, post_range, cloud_lt=cloud_lt)
    diagnostics["post_n_candidates"] = len(post_items)
    diagnostics["post_candidate_dates"] = [
        _scene_date(it).isoformat() for it in post_items[:12] if _scene_date(it)
    ]

    # Prefer chronological first in post window among low-cloud set (re-sort by date)
    post_by_date = sorted(
        [it for it in post_items if _scene_date(it)],
        key=lambda it: (_scene_date(it), it.properties.get("eo:cloud_cover", 100)),
    )
    if post_by_date:
        it = post_by_date[0]
        d = _scene_date(it)
        method = (
            f"first_clear_post_khareef in {post_range}; "
            f"product={it.id}; cloud={it.properties.get('eo:cloud_cover')}; "
            f"tile={it.properties.get('s2:mgrs_tile')} "
            "(dynamic T0 — not fixed calendar; not live onset detection)"
        )
        diagnostics["t0_source_window"] = "post_khareef"
        diagnostics["t0_product_id"] = it.id
        return d, method, diagnostics

    onset_items = list_s2_candidates(bbox, onset_range, cloud_lt=cloud_lt)
    diagnostics["onset_n_candidates"] = len(onset_items)
    diagnostics["onset_candidate_dates"] = [
        _scene_date(it).isoformat() for it in onset_items[:12] if _scene_date(it)
    ]
    onset_by_date = sorted(
        [it for it in onset_items if _scene_date(it)],
        key=lambda it: (_scene_date(it), it.properties.get("eo:cloud_cover", 100)),
    )
    if onset_by_date:
        it = onset_by_date[0]
        d = _scene_date(it)
        method = (
            f"fallback_first_clear_onset in {onset_range} "
            f"(post-khareef window {post_range} had 0 STAC candidates or none usable); "
            f"product={it.id}; cloud={it.properties.get('eo:cloud_cover')}; "
            f"tile={it.properties.get('s2:mgrs_tile')} "
            "(dynamic T0 — documented search, not live Khareef onset detector)"
        )
        diagnostics["t0_source_window"] = "onset"
        diagnostics["t0_product_id"] = it.id
        return d, method, diagnostics

    diagnostics["t0_source_window"] = None
    return None, "no_clear_scene_in_post_or_onset_windows", diagnostics


def fetch_ndmi_for_lag(
    bbox: list[float],
    target: date,
    out_shape: tuple[int, int],
    half_days: int = MPI_SEARCH_HALF_WINDOW_DAYS,
    cloud_lt: float = 40.0,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    """
    Multi-scene search ±half_days around target; try scenes by ascending cloud.
    First scene with SCL clear_frac ≥ MIN_CLEAR_FRAC wins. Else gap (null NDMI).
    """
    dr = date_window(target, half_days)
    items = list_s2_candidates(bbox, dr, cloud_lt=cloud_lt)
    info: dict[str, Any] = {
        "lag_target": target.isoformat(),
        "search_range": dr,
        "n_candidates": len(items),
        "status": None,
    }
    if not items:
        info["status"] = "gap"
        info["reason"] = f"No S2 L2A scenes with eo:cloud_cover < {cloud_lt} in {dr}"
        return None, info

    tried = []
    for item in items:
        ndmi, scene_info = rp.fetch_ndmi_scl(
            bbox,
            # Pin to this product's date day so fetch_ndmi_scl picks lowest cloud that day;
            # we already ordered candidates — pass a 1-day range around scene date.
            f"{_scene_date(item).isoformat()}/{_scene_date(item).isoformat()}"
            if _scene_date(item)
            else dr,
            out_shape,
        )
        # Prefer exact product: if fetch picked a different one, still accept if ok
        tried.append(
            {
                "wanted": item.id,
                "got": scene_info.get("product_id"),
                "status": scene_info.get("status"),
                "clear_frac": scene_info.get("clear_frac"),
                "cloud_cover": scene_info.get("cloud_cover"),
            }
        )
        if ndmi is not None and scene_info.get("status") == "ok":
            info.update(scene_info)
            info["status"] = "ok"
            info["tried"] = tried
            return ndmi, info

    info["status"] = "gap"
    info["reason"] = (
        f"All {len(items)} candidate(s) in {dr} failed SCL clear gate "
        f"(min clear_frac={MIN_CLEAR_FRAC}); no fabricated NDMI"
    )
    info["tried"] = tried
    return None, info


def cell_ndmi_mean(ndmi: np.ndarray | None, r_frac: float, c_frac: float, half: int = 2) -> float | None:
    if ndmi is None:
        return None
    h, w = ndmi.shape
    pr = min(max(int(r_frac * h), 0), h - 1)
    pc = min(max(int(c_frac * w), 0), w - 1)
    block = ndmi[max(0, pr - half) : pr + half + 1, max(0, pc - half) : pc + half + 1]
    finite = block[np.isfinite(block)]
    if finite.size == 0:
        return None
    return float(np.mean(finite))


def dry_run() -> int:
    MPI_DIR.mkdir(parents=True, exist_ok=True)
    ladder = regeneration_ladder_doc()
    write_json(MPI_DIR / "regeneration_ladder.stubs.json", ladder)
    curve = {
        "generated_at": utc_now_iso(),
        "status": "dry_run",
        "layer": LAYER_MPI,
        "provisional": True,
        "pilot_bbox": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "message": (
            "Dry-run only — Planetary Computer not queried. "
            "No fabricated NDMI/MPI values."
        ),
        "t0_method": None,
        "t0_date": None,
        "lags_weeks": list(MPI_LAGS_WEEKS),
        "points": [],
        "disclaimer_en": (
            "NDMI and MPI are satellite moisture proxies, not soil moisture %."
        ),
    }
    write_json(MPI_DIR / "mpi_curve.json", curve)
    write_json(
        MPI_DIR / "mpi_cells.geojson",
        {
            "type": "FeatureCollection",
            "generated_at": utc_now_iso(),
            "status": "dry_run",
            "layer": LAYER_MPI,
            "provisional": True,
            "pilot_bbox": PILOT_BBOX,
            "features": [],
            "note": "Empty — dry-run; no fabricated MPI.",
        },
    )
    meta = {
        "generated_at": utc_now_iso(),
        "status": "dry_run",
        "layer": LAYER_MPI,
        "provisional": True,
        "pilot_bbox": PILOT_BBOX,
        "ui_wire": False,
        "artifacts_root": "satellite/pipeline/artifacts/mountain_pilot/",
        "message": "Dry-run — schema/stubs only",
        "forbidden_partner_keys": sorted(FORBIDDEN_PARTNER_KEYS),
    }
    write_json(MPI_DIR / "mpi_run_meta.json", meta)
    # Refresh terrain schema via pilot dry-run helpers without PC
    rp.OUT_DIR = OUT_DIR
    rp.GEOJSON_PATH = OUT_DIR / "pilot_terrain.geojson"
    rp.META_PATH = OUT_DIR / "run_meta.json"
    rp.SCHEMA_PATH = OUT_DIR / "pilot_terrain.schema.json"
    write_json(rp.SCHEMA_PATH, rp.schema_doc())
    print(f"[dry-run] mpi stubs → {MPI_DIR}")
    return 0


def refresh_stratified_terrain_sample(
    features: list[dict[str, Any]],
    dem_source: str,
    extra_meta: dict[str, Any],
) -> Path:
    """Rewrite pilot_terrain.sample.geojson with elev×slope strata (not first-50)."""
    elevs = np.array(
        [f["properties"].get("elevation_m", float("nan")) for f in features], dtype="float64"
    )
    slopes = np.array(
        [f["properties"].get("slope_deg", float("nan")) for f in features], dtype="float64"
    )
    idxs = stratified_sample_indices(elevs, slopes, n_total=48)
    sample_feats = [features[i] for i in idxs]

    # Annotate stratum labels for science review
    fe = elevs[np.isfinite(elevs)]
    fs = slopes[np.isfinite(slopes)]
    elev_edges = np.quantile(fe, [0, 1 / 3, 2 / 3, 1]) if fe.size else [0, 0, 0, 0]
    slope_med = float(np.median(fs)) if fs.size else 0.0
    for f in sample_feats:
        e = f["properties"].get("elevation_m")
        s = f["properties"].get("slope_deg")
        if e is None or s is None:
            continue
        if e <= elev_edges[1]:
            eband = "low_elev"
        elif e <= elev_edges[2]:
            eband = "mid_elev"
        else:
            eband = "high_elev"
        sband = "gentle" if s < slope_med else "steep"
        f["properties"]["sample_stratum"] = f"{eband}_{sband}"
        f["properties"]["sample_method"] = "stratified_elev_tertile_x_slope_median"
        assert_no_forbidden_partner_keys(f["properties"])

    sample_path = OUT_DIR / "pilot_terrain.sample.geojson"
    fc = {
        "type": "FeatureCollection",
        "generated_at": utc_now_iso(),
        "pilot_bbox": PILOT_BBOX,
        "status": STATUS_PILOT,
        "layer": "mountain_pilot",
        "dem_source": dem_source,
        "bbox_note": BBOX_LOCK_NOTE,
        "sample_method": "stratified_elev_tertile_x_slope_median",
        "n_sample": len(sample_feats),
        "n_universe": len(features),
        "elev_tertile_edges_m": [round(float(x), 1) for x in elev_edges],
        "slope_median_deg": round(slope_med, 2),
        "features": sample_feats,
        "note_sample": (
            "Stratified sample (low/mid/high elev × gentle/steep) — not first-N high-elev. "
            "Full grid: pilot_terrain.geojson (gitignored)."
        ),
        **{k: v for k, v in extra_meta.items() if k in ("ndmi_pre", "ndmi_post", "grid_cell_m")},
    }
    write_json(sample_path, fc)
    return sample_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase-2 offline MPI curve (mountain_pilot artifacts only)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--post-range",
        default="2026-09-15/2026-10-31",
        help="Post-khareef / late Sep–Oct window for preferred T0 (default 2026-09-15/2026-10-31)",
    )
    parser.add_argument(
        "--onset-range",
        default="2026-06-01/2026-06-21",
        help="Onset / post-onset search window if post-khareef has no clear scenes",
    )
    parser.add_argument(
        "--pre-range",
        default="2026-05-01/2026-05-31",
        help="Optional pre-khareef context NDMI (terrain refresh)",
    )
    parser.add_argument("--grid-m", type=float, default=250.0)
    parser.add_argument("--cloud-lt", type=float, default=40.0)
    parser.add_argument("--out-shape", type=int, default=200, help="NDMI read shape (square)")
    parser.add_argument("--max-cells", type=int, default=120, help="Max cells for MPI curve sampling")
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MPI_DIR.mkdir(parents=True, exist_ok=True)

    # Always emit regen stubs (offline JSON; no UI)
    write_json(MPI_DIR / "regeneration_ladder.stubs.json", regeneration_ladder_doc())

    if args.dry_run:
        return dry_run()

    print(f"[{utc_now_iso()}] MPI phase-2 bbox={PILOT_BBOX}")
    print(f"  post-range (preferred T0)={args.post_range}")
    print(f"  onset-range (fallback T0)={args.onset_range}")

    # --- DEM ---
    try:
        dem, transform, crs, dem_source = rp.fetch_dem(PILOT_BBOX)
    except Exception as exc:
        meta = {
            "generated_at": utc_now_iso(),
            "status": STATUS_INSUFFICIENT,
            "layer": LAYER_MPI,
            "provisional": True,
            "pilot_bbox": PILOT_BBOX,
            "message": f"DEM fetch failed: {exc}",
            "ui_wire": False,
        }
        write_json(MPI_DIR / "mpi_run_meta.json", meta)
        write_json(
            MPI_DIR / "mpi_curve.json",
            {**meta, "points": [], "mpi_class": None, "t0_date": None},
        )
        print(f"[stop] DEM failed: {exc}")
        return 2

    mid_lat = (PILOT_BBOX[1] + PILOT_BBOX[3]) / 2.0
    if abs(transform.a) < 1.0:
        pixel_size_m = abs(transform.a) * 111_320.0 * math.cos(math.radians(mid_lat))
    else:
        pixel_size_m = abs(transform.a)

    slope_deg, aspect_deg = rp.slope_aspect(dem, pixel_size_m)
    flow = rp.flow_accum_proxy(dem)
    twi_arr = rp.twi_from(slope_deg, flow)
    elev_finite = dem[np.isfinite(dem)]
    slope_finite = slope_deg[np.isfinite(slope_deg)]
    p90 = float(np.nanpercentile(slope_finite, 90)) if slope_finite.size else 0.0
    print(f"[dem] {dem_source}; shape={dem.shape}; px≈{pixel_size_m:.1f}m; slope_p90={p90:.2f}")

    # --- T0 ---
    t0, t0_method, t0_diag = pick_t0(
        PILOT_BBOX, args.post_range, args.onset_range, cloud_lt=args.cloud_lt
    )
    print(f"[t0] date={t0} method={t0_method}")
    print(f"[t0] diagnostics={json.dumps(t0_diag, ensure_ascii=False)[:500]}")

    out_shape = (args.out_shape, args.out_shape)
    lag_rasters: dict[int, np.ndarray | None] = {}
    lag_infos: dict[int, dict[str, Any]] = {}

    if t0 is None:
        curve = {
            "generated_at": utc_now_iso(),
            "status": STATUS_INSUFFICIENT,
            "layer": LAYER_MPI,
            "provisional": True,
            "pilot_bbox": PILOT_BBOX,
            "bbox_note": BBOX_LOCK_NOTE,
            "t0_date": None,
            "t0_method": t0_method,
            "t0_diagnostics": t0_diag,
            "lags_weeks": list(MPI_LAGS_WEEKS),
            "points": [],
            "mpi_class": None,
            "n_valid": 0,
            "message": (
                "No clear S2 scene in preferred post-khareef (late Sep–Oct) or onset windows. "
                "Fail-honest — no fabricated NDMI/MPI. "
                "Note: if catalog has not ingested late Sep–Oct yet, re-run after clearer scenes."
            ),
            "disclaimer_en": (
                "NDMI and MPI are satellite moisture proxies, not soil moisture %."
            ),
        }
        write_json(MPI_DIR / "mpi_curve.json", curve)
        write_json(
            MPI_DIR / "mpi_cells.geojson",
            {
                "type": "FeatureCollection",
                "generated_at": utc_now_iso(),
                "status": STATUS_INSUFFICIENT,
                "layer": LAYER_MPI,
                "provisional": True,
                "pilot_bbox": PILOT_BBOX,
                "features": [],
                "message": curve["message"],
            },
        )
        write_json(
            MPI_DIR / "mpi_run_meta.json",
            {
                "generated_at": utc_now_iso(),
                "status": STATUS_INSUFFICIENT,
                "layer": LAYER_MPI,
                "provisional": True,
                "pilot_bbox": PILOT_BBOX,
                "dem_source": dem_source,
                "t0_method": t0_method,
                "t0_diagnostics": t0_diag,
                "post_range": args.post_range,
                "onset_range": args.onset_range,
                "ui_wire": False,
                "message": curve["message"],
            },
        )
        print("[stop] insufficient clear for T0 — exit honest")
        return 2

    # Fetch NDMI stacks for each lag (±3d multi-scene)
    for lag in MPI_LAGS_WEEKS:
        target = t0 + timedelta(weeks=lag)
        print(f"[ndmi] lag=T+{lag}w target={target.isoformat()} ±{MPI_SEARCH_HALF_WINDOW_DAYS}d")
        ndmi, info = fetch_ndmi_for_lag(
            PILOT_BBOX, target, out_shape, cloud_lt=args.cloud_lt
        )
        lag_rasters[lag] = ndmi
        lag_infos[lag] = info
        print(f"  → status={info.get('status')} clear_frac={info.get('clear_frac')} "
              f"date={info.get('date')} product={info.get('product_id')}")

    # AOI-mean curve (science summary)
    aoi_points = []
    aoi_ndmi_by_lag: dict[int, float | None] = {}
    for lag in MPI_LAGS_WEEKS:
        ndmi = lag_rasters[lag]
        info = lag_infos[lag]
        if ndmi is not None:
            finite = ndmi[np.isfinite(ndmi)]
            mean_v = float(np.mean(finite)) if finite.size else None
        else:
            mean_v = None
        aoi_ndmi_by_lag[lag] = mean_v
        aoi_points.append(
            {
                "lag_weeks": lag,
                "target_date": (t0 + timedelta(weeks=lag)).isoformat(),
                "search_range": info.get("search_range"),
                "ndmi_mean": None if mean_v is None else round(mean_v, 4),
                "status": "ok" if mean_v is not None else "gap",
                "product_id": info.get("product_id"),
                "scene_date": info.get("date"),
                "tile": info.get("tile"),
                "cloud_cover": info.get("cloud_cover"),
                "clear_frac": info.get("clear_frac"),
                "reason": info.get("reason"),
            }
        )

    aoi_class, aoi_reason, aoi_n_valid = classify_mpi(
        aoi_ndmi_by_lag, DEFAULT_DRY_BASELINE_NDMI
    )
    curve_status = STATUS_PILOT if aoi_n_valid >= 2 else STATUS_INSUFFICIENT

    curve = {
        "generated_at": utc_now_iso(),
        "status": curve_status,
        "layer": LAYER_MPI,
        "provisional": True,
        "pilot_bbox": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "t0_date": t0.isoformat(),
        "t0_method": t0_method,
        "t0_diagnostics": t0_diag,
        "dry_baseline_ndmi": DEFAULT_DRY_BASELINE_NDMI,
        "lags_weeks": list(MPI_LAGS_WEEKS),
        "search_half_window_days": MPI_SEARCH_HALF_WINDOW_DAYS,
        "points": aoi_points,
        "mpi_class": aoi_class,
        "mpi_class_reason": aoi_reason,
        "n_valid": aoi_n_valid,
        "dem_source": dem_source,
        "disclaimer_en": (
            "NDMI and MPI are satellite moisture proxies, not soil moisture %. "
            "Classes provisional / pilot_unverified until field validation. "
            "Gaps are null — never interpolated."
        ),
        "science_lock": "SCIENCE_LOCKS_v0.4_phase1_2.md §5",
    }
    write_json(MPI_DIR / "mpi_curve.json", curve)

    # --- Build terrain cells + MPI per stratified subset ---
    import rasterio
    from shapely.geometry import box, mapping

    h, w = dem.shape
    grid_cell_m = float(args.grid_m)
    step = max(1, int(round(grid_cell_m / max(pixel_size_m, 1.0))))
    source_str = f"{dem_source}; {SOURCE_S2}"
    all_features: list[dict[str, Any]] = []

    for r in range(0, h, step):
        for c in range(0, w, step):
            block_elev = dem[r : r + step, c : c + step]
            if not np.any(np.isfinite(block_elev)):
                continue
            row_c = r + min(step, block_elev.shape[0]) / 2.0
            col_c = c + min(step, block_elev.shape[1]) / 2.0
            lon, lat = rasterio.transform.xy(transform, row_c, col_c)
            half_lon, half_lat = rp.cell_half_deg(float(lat), grid_cell_m)
            props: dict[str, Any] = {
                "elevation_m": round(float(np.nanmean(block_elev)), 1),
                "slope_deg": round(float(np.nanmean(slope_deg[r : r + step, c : c + step])), 2),
                "aspect_deg": round(float(np.nanmean(aspect_deg[r : r + step, c : c + step])), 1),
                "twi": round(float(np.nanmean(twi_arr[r : r + step, c : c + step])), 3),
                "twi_note": "Topographic Wetness Proxy (coarse) — not full hydrology",
                "status": STATUS_PILOT,
                "layer": "mountain_pilot",
                "source": source_str,
                "note": (
                    "Raw terrain / moisture proxy only. No suitability, action ladder, "
                    "or species. NDMI ≠ soil moisture %."
                ),
                "_row_frac": float(r / h),
                "_col_frac": float(c / w),
            }
            # Optional provisional terrain stubs (labeled)
            props["terrain_evidence_provisional"] = True
            props["hydrology_evidence_provisional"] = True
            assert_no_forbidden_partner_keys(props)
            all_features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(
                        box(lon - half_lon, lat - half_lat, lon + half_lon, lat + half_lat)
                    ),
                    "properties": props,
                }
            )

    # Full terrain geojson (gitignored) + stratified sample (committed)
    # Strip internal fracs from published terrain props after sampling
    terrain_fc_features = []
    for f in all_features:
        p = {k: v for k, v in f["properties"].items() if not k.startswith("_")}
        terrain_fc_features.append({"type": "Feature", "geometry": f["geometry"], "properties": p})

    # Optional pre/post context on terrain (fail-honest)
    print(f"[terrain-ndmi] pre={args.pre_range} post={args.post_range}")
    ndmi_pre, pre_info = rp.fetch_ndmi_scl(PILOT_BBOX, args.pre_range, out_shape)
    ndmi_post, post_info = rp.fetch_ndmi_scl(PILOT_BBOX, args.post_range, out_shape)
    print(f"  pre={pre_info.get('status')} post={post_info.get('status')}")

    for f, raw in zip(terrain_fc_features, all_features):
        rf = raw["properties"]["_row_frac"]
        cf = raw["properties"]["_col_frac"]
        if ndmi_pre is not None:
            v = cell_ndmi_mean(ndmi_pre, rf, cf)
            if v is not None:
                f["properties"]["ndmi_pre_khareef"] = round(v, 4)
        if ndmi_post is not None:
            v = cell_ndmi_mean(ndmi_post, rf, cf)
            if v is not None:
                f["properties"]["ndmi_post_khareef"] = round(v, 4)
        if "ndmi_pre_khareef" in f["properties"] and "ndmi_post_khareef" in f["properties"]:
            f["properties"]["ndmi_delta"] = round(
                f["properties"]["ndmi_post_khareef"] - f["properties"]["ndmi_pre_khareef"], 4
            )

    terrain_fc = {
        "type": "FeatureCollection",
        "generated_at": utc_now_iso(),
        "pilot_bbox": PILOT_BBOX,
        "status": STATUS_PILOT,
        "layer": "mountain_pilot",
        "dem_source": dem_source,
        "bbox_note": BBOX_LOCK_NOTE,
        "ndmi_pre": pre_info,
        "ndmi_post": post_info,
        "grid_cell_m": grid_cell_m,
        "n_features": len(terrain_fc_features),
        "features": terrain_fc_features,
    }
    write_json(OUT_DIR / "pilot_terrain.geojson", terrain_fc)

    sample_path = refresh_stratified_terrain_sample(
        terrain_fc_features,
        dem_source,
        {"ndmi_pre": pre_info, "ndmi_post": post_info, "grid_cell_m": grid_cell_m},
    )

    # MPI cells: stratified subset
    elevs = np.array([f["properties"]["elevation_m"] for f in all_features], dtype="float64")
    slopes = np.array([f["properties"]["slope_deg"] for f in all_features], dtype="float64")
    mpi_idxs = stratified_sample_indices(elevs, slopes, n_total=min(args.max_cells, 120))

    mpi_features = []
    class_counts = {"High": 0, "Medium": 0, "Low": 0, "Insufficient": 0}
    for i in mpi_idxs:
        raw = all_features[i]
        rf = raw["properties"]["_row_frac"]
        cf = raw["properties"]["_col_frac"]
        ndmi_by_lag: dict[int, float | None] = {}
        curve_pts = []
        for lag in MPI_LAGS_WEEKS:
            v = cell_ndmi_mean(lag_rasters[lag], rf, cf)
            ndmi_by_lag[lag] = v
            info = lag_infos[lag]
            curve_pts.append(
                {
                    "lag_weeks": lag,
                    "ndmi": None if v is None else round(v, 4),
                    "status": "ok" if v is not None else "gap",
                    "scene_date": info.get("date"),
                    "product_id": info.get("product_id"),
                    "cloud_cover": info.get("cloud_cover"),
                    "clear_frac": info.get("clear_frac"),
                }
            )
        mclass, mreason, n_valid = classify_mpi(ndmi_by_lag, DEFAULT_DRY_BASELINE_NDMI)
        if mclass is None:
            class_counts["Insufficient"] += 1
            class_label = "Insufficient"
        else:
            class_counts[mclass] = class_counts.get(mclass, 0) + 1
            class_label = mclass

        props = {
            "elevation_m": raw["properties"]["elevation_m"],
            "slope_deg": raw["properties"]["slope_deg"],
            "aspect_deg": raw["properties"]["aspect_deg"],
            "twi": raw["properties"]["twi"],
            "twi_note": "Topographic Wetness Proxy (coarse) — not full hydrology",
            "t0_date": t0.isoformat(),
            "mpi_curve": curve_pts,
            "mpi_n_valid": n_valid,
            "mpi_class": class_label if class_label != "Insufficient" else None,
            "mpi_class_display": class_label,
            "mpi_class_reason": mreason,
            "status": STATUS_PILOT if n_valid >= 2 else STATUS_INSUFFICIENT,
            "layer": LAYER_MPI,
            "provisional": True,
            "degradation_evidence_provisional": None,  # stub field, unlabeled value
            "terrain_evidence_provisional": True,
            "hydrology_evidence_provisional": True,
            "source": source_str,
            "source_citations": [
                {
                    "lag_weeks": lag,
                    "product_id": lag_infos[lag].get("product_id"),
                    "date": lag_infos[lag].get("date"),
                    "tile": lag_infos[lag].get("tile"),
                    "cloud_cover": lag_infos[lag].get("cloud_cover"),
                    "clear_frac": lag_infos[lag].get("clear_frac"),
                    "status": lag_infos[lag].get("status"),
                }
                for lag in MPI_LAGS_WEEKS
            ],
            "note": (
                "Offline MPI evidence only (pilot_unverified / provisional). "
                "NDMI/MPI ≠ soil moisture %. No suitability→action auto-assign. "
                "Not for partner Map/Analysis/Restoration UI."
            ),
            "sample_method": "stratified_elev_tertile_x_slope_median",
        }
        # stratum tag
        fe = elevs[np.isfinite(elevs)]
        elev_edges = np.quantile(fe, [0, 1 / 3, 2 / 3, 1]) if fe.size else [0, 0, 0, 0]
        slope_med = float(np.median(slopes[np.isfinite(slopes)])) if slopes.size else 0.0
        e = props["elevation_m"]
        s = props["slope_deg"]
        if e <= elev_edges[1]:
            eband = "low_elev"
        elif e <= elev_edges[2]:
            eband = "mid_elev"
        else:
            eband = "high_elev"
        props["sample_stratum"] = f"{eband}_{'gentle' if s < slope_med else 'steep'}"
        assert_no_forbidden_partner_keys(props)
        mpi_features.append(
            {"type": "Feature", "geometry": raw["geometry"], "properties": props}
        )

    mpi_fc = {
        "type": "FeatureCollection",
        "generated_at": utc_now_iso(),
        "pilot_bbox": PILOT_BBOX,
        "status": curve_status,
        "layer": LAYER_MPI,
        "provisional": True,
        "dem_source": dem_source,
        "t0_date": t0.isoformat(),
        "t0_method": t0_method,
        "n_features": len(mpi_features),
        "class_counts": class_counts,
        "aoi_mpi_class": aoi_class,
        "disclaimer_en": curve["disclaimer_en"],
        "ui_wire": False,
        "features": mpi_features,
    }
    write_json(MPI_DIR / "mpi_cells.geojson", mpi_fc)

    # Compact sample of mpi cells for git if large
    mpi_sample = {k: v for k, v in mpi_fc.items() if k != "features"}
    mpi_sample["features"] = mpi_features[:48]
    mpi_sample["note_sample"] = "Up to 48 stratified MPI cells for review."
    write_json(MPI_DIR / "mpi_cells.sample.geojson", mpi_sample)

    run_meta = {
        "generated_at": utc_now_iso(),
        "status": curve_status,
        "layer": LAYER_MPI,
        "provisional": True,
        "pilot_bbox": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "dem_source": dem_source,
        "dem_note": "Copernicus DEM GLO-30 via PC (NASADEM fallback in shared helper)",
        "twi_note": "Topographic Wetness Proxy only — not depression-filled D8 hydrology",
        "slope_p90_deg": p90,
        "t0_date": t0.isoformat(),
        "t0_method": t0_method,
        "t0_diagnostics": t0_diag,
        "post_range": args.post_range,
        "onset_range": args.onset_range,
        "pre_range": args.pre_range,
        "search_half_window_days": MPI_SEARCH_HALF_WINDOW_DAYS,
        "lags_weeks": list(MPI_LAGS_WEEKS),
        "lag_scene_info": {str(k): v for k, v in lag_infos.items()},
        "aoi_mpi_class": aoi_class,
        "aoi_mpi_class_reason": aoi_reason,
        "aoi_n_valid": aoi_n_valid,
        "class_counts": class_counts,
        "n_terrain_features": len(terrain_fc_features),
        "n_mpi_features": len(mpi_features),
        "ndmi_pre": pre_info,
        "ndmi_post": post_info,
        "artifacts": {
            "mpi_curve": str((MPI_DIR / "mpi_curve.json").relative_to(REPO_ROOT)),
            "mpi_cells": str((MPI_DIR / "mpi_cells.geojson").relative_to(REPO_ROOT)),
            "mpi_cells_sample": str((MPI_DIR / "mpi_cells.sample.geojson").relative_to(REPO_ROOT)),
            "mpi_run_meta": str((MPI_DIR / "mpi_run_meta.json").relative_to(REPO_ROOT)),
            "regen_stubs": str((MPI_DIR / "regeneration_ladder.stubs.json").relative_to(REPO_ROOT)),
            "terrain_sample": str(sample_path.relative_to(REPO_ROOT)),
            "terrain_full": str((OUT_DIR / "pilot_terrain.geojson").relative_to(REPO_ROOT)),
            "run_meta_terrain": str((OUT_DIR / "run_meta.json").relative_to(REPO_ROOT)),
        },
        "ui_wire": False,
        "app_public_write": False,
        "forbidden_partner_keys": sorted(FORBIDDEN_PARTNER_KEYS),
        "science_lock": "SCIENCE_LOCKS_v0.4_phase1_2.md §5 + §6",
        "disclaimer_en": curve["disclaimer_en"],
    }
    write_json(MPI_DIR / "mpi_run_meta.json", run_meta)

    # Update parent run_meta.json (terrain) with phase-2 pointer
    terrain_meta = {
        "generated_at": utc_now_iso(),
        "status": STATUS_PILOT,
        "layer": "mountain_pilot",
        "pilot_bbox": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "dem_source": dem_source,
        "slope_p90_deg": p90,
        "n_features": len(terrain_fc_features),
        "ndmi_pre": pre_info,
        "ndmi_post": post_info,
        "sample_method": "stratified_elev_tertile_x_slope_median",
        "phase2_mpi": {
            "layer": LAYER_MPI,
            "t0_date": t0.isoformat(),
            "aoi_mpi_class": aoi_class,
            "status": curve_status,
            "artifacts_dir": "satellite/pipeline/artifacts/mountain_pilot/mpi/",
        },
        "artifacts": {
            "geojson": str((OUT_DIR / "pilot_terrain.geojson").relative_to(REPO_ROOT)),
            "sample": str(sample_path.relative_to(REPO_ROOT)),
            "schema": str((OUT_DIR / "pilot_terrain.schema.json").relative_to(REPO_ROOT)),
            "mpi_run_meta": str((MPI_DIR / "mpi_run_meta.json").relative_to(REPO_ROOT)),
        },
        "ui_wire": False,
        "forbidden_fields_enforced": sorted(rp.FORBIDDEN_PROP_KEYS),
    }
    write_json(OUT_DIR / "run_meta.json", terrain_meta)
    write_json(OUT_DIR / "pilot_terrain.schema.json", rp.schema_doc())

    print(f"wrote AOI curve class={aoi_class} n_valid={aoi_n_valid} → {MPI_DIR / 'mpi_curve.json'}")
    print(f"wrote {len(mpi_features)} MPI cells → {MPI_DIR / 'mpi_cells.geojson'}")
    print(f"stratified terrain sample → {sample_path}")
    print(f"meta → {MPI_DIR / 'mpi_run_meta.json'}")
    return 0 if aoi_n_valid >= 2 or t0 is not None else 2


if __name__ == "__main__":
    sys.exit(main())
