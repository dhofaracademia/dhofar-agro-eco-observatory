#!/usr/bin/env python3
"""
run_mountain_pilot.py — Round-4 Track 2 mountain pilot (raw grid ONLY).

Base: AgriTech pilot draft (2026-09-08). Adapted for CoS science lock:
  - Locked start bbox WGS84 [W,S,E,N]: [54.05, 17.08, 54.22, 17.22]
    (Jabal Qara fog-escarpment). No change before first run; after DEM
    visual check may nudge ≤0.05°; max span ≤~0.2° per side.
  - Outputs under satellite/pipeline/artifacts/mountain_pilot/ ONLY —
    NOT under app/public (no partner UI wire until science spot-check).
  - Stamp status: pilot_unverified, layer: mountain_pilot.
  - Forbidden in feature properties: suitability, ecological confidence,
    action ladder, species, live MPI class.
  - Fog-only T. dhofarica remains a science lock — this pilot must not
    invent species fields.

WHAT IT COMPUTES (real terrain + moisture proxies):
  1. Copernicus DEM GLO-30 (30 m) via Planetary Computer; SRTM fallback.
  2. Slope / aspect (Horn-style via np.gradient) + elevation.
  3. TWI proxy = ln(flow_accum / tan(slope)) — coarse D8-neighbor proxy,
     NOT a full hydrology model.
  4. Sentinel-2 L2A NDMI with SCL fail-honest masking (strict cloud).
     Insufficient clear → exit with honest status (no fabricated NDMI).

HONEST STATUS: treat every number as unverified until science spot-check.
Do NOT wire into Map / Gallery / Restoration UI yet.

USAGE:
  python satellite/pipeline/run_mountain_pilot.py
  python satellite/pipeline/run_mountain_pilot.py --dry-run   # schema + stub only
  MOUNTAIN_PILOT_OUT=... python ...   # override artifact dir

Phase-2 MPI curve (offline): see run_mountain_mpi.py → artifacts/mountain_pilot/mpi/
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parents[1]
DEFAULT_OUT = PIPELINE_DIR / "artifacts" / "mountain_pilot"
OUT_DIR = Path(os.environ.get("MOUNTAIN_PILOT_OUT", str(DEFAULT_OUT)))
GEOJSON_PATH = OUT_DIR / "pilot_terrain.geojson"
META_PATH = OUT_DIR / "run_meta.json"
SCHEMA_PATH = OUT_DIR / "pilot_terrain.schema.json"

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

# CoS / AgriTech locked start bbox — Jabal Qara fog-escarpment.
# Do not change before first DEM visual check. Nudge ≤0.05° only with note.
PILOT_BBOX = [54.05, 17.08, 54.22, 17.22]  # W, S, E, N (WGS84)
BBOX_LOCK_NOTE = (
    "Locked start bbox [54.05, 17.08, 54.22, 17.22] (Jabal Qara fog-escarpment). "
    "No change before first run; post-DEM nudge ≤0.05°; max span ≤~0.2°/side."
)

CLOUD_LT = 20.0  # STAC eo:cloud_cover filter (scene-level)
# SCL classes treated as clear for NDMI (fail-honest: everything else masked).
# 4=vegetation, 5=not_vegetated, 6=water, 7=unclassified (kept sparsely).
SCL_CLEAR = {4, 5, 6, 7}
MIN_CLEAR_FRAC = 0.15  # below this → insufficient clear data
GRID_CELL_M_DEFAULT = 250.0  # pilot default; use --grid-m 100 for finer local runs
SCALE = 10000.0
FLAT_SLOPE_P90_DEG = 2.0  # if p90 slope below this → flat window, stop
SOURCE_DEM_PRIMARY = "Copernicus DEM GLO-30 via Microsoft Planetary Computer"
SOURCE_DEM_FALLBACK = "NASADEM / SRTM (nasadem collection) via Microsoft Planetary Computer"
SOURCE_S2 = "Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer"

FORBIDDEN_PROP_KEYS = {
    "suitability",
    "confidence",
    "ecological_confidence",
    "action",
    "action_ladder",
    "species",
    "species_note",
    "mpi_class",
    "mpi",
    "live_mpi",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def schema_doc() -> dict[str, Any]:
    """Sample schema for CI / offline review (no fabricated measurements)."""
    return {
        "type": "FeatureCollection",
        "required_collection_fields": [
            "type",
            "generated_at",
            "pilot_bbox",
            "status",
            "layer",
            "dem_source",
            "features",
        ],
        "status_enum": ["pilot_unverified", "insufficient_clear_data", "flat_or_arid_stop", "dry_run"],
        "layer": "mountain_pilot",
        "feature_properties_allowed": [
            "elevation_m",
            "slope_deg",
            "aspect_deg",
            "twi",
            "ndmi_pre_khareef",
            "ndmi_post_khareef",
            "ndmi_delta",
            "clear_frac",
            "source",
            "note",
            "status",
            "layer",
        ],
        "feature_properties_forbidden": sorted(FORBIDDEN_PROP_KEYS),
        "pilot_bbox_locked": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "example_feature": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [54.10, 17.12],
                        [54.101, 17.12],
                        [54.101, 17.121],
                        [54.10, 17.121],
                        [54.10, 17.12],
                    ]
                ],
            },
            "properties": {
                "elevation_m": 650.0,
                "slope_deg": 12.3,
                "aspect_deg": 210.0,
                "twi": 4.2,
                "ndmi_pre_khareef": -0.05,
                "ndmi_post_khareef": 0.12,
                "ndmi_delta": 0.17,
                "clear_frac": 0.62,
                "status": "pilot_unverified",
                "layer": "mountain_pilot",
                "source": SOURCE_DEM_PRIMARY + "; " + SOURCE_S2,
                "note": "Raw terrain/moisture only — no suitability / action / species.",
            },
        },
    }


def dry_run() -> int:
    """Ship schema + honest not-yet-run meta without hitting PC."""
    write_json(SCHEMA_PATH, schema_doc())
    meta = {
        "generated_at": utc_now(),
        "status": "dry_run",
        "layer": "mountain_pilot",
        "pilot_bbox": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "message": (
            "Dry-run only — Planetary Computer not queried. "
            "Script + schema shipped; full E2E not yet run in this invocation."
        ),
        "artifacts": {
            "schema": str(SCHEMA_PATH.relative_to(REPO_ROOT)),
            "geojson": None,
        },
    }
    write_json(META_PATH, meta)
    stub = {
        "type": "FeatureCollection",
        "generated_at": utc_now(),
        "pilot_bbox": PILOT_BBOX,
        "status": "dry_run",
        "layer": "mountain_pilot",
        "dem_source": None,
        "bbox_note": BBOX_LOCK_NOTE,
        "features": [],
        "note": "Empty FeatureCollection — dry-run; no fabricated NDMI/DEM values.",
    }
    write_json(GEOJSON_PATH, stub)
    print(f"[dry-run] wrote schema → {SCHEMA_PATH}")
    print(f"[dry-run] wrote stub geojson → {GEOJSON_PATH}")
    print(f"[dry-run] wrote meta → {META_PATH}")
    return 0


def open_catalog():
    import planetary_computer as pc
    from pystac_client import Client

    return Client.open(STAC_URL, modifier=pc.sign_inplace)


def _read_dem_window(href: str, bbox: list[float]):
    import rasterio
    from pyproj import Transformer
    from rasterio.windows import from_bounds

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_PROTOCOLS="https",
    ):
        with rasterio.open(href) as src:
            if src.crs and str(src.crs) not in ("EPSG:4326", "OGC:CRS84"):
                transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                left, bottom = transformer.transform(bbox[0], bbox[1])
                right, top = transformer.transform(bbox[2], bbox[3])
                bounds = (left, bottom, right, top)
            else:
                bounds = (bbox[0], bbox[1], bbox[2], bbox[3])
            window = from_bounds(*bounds, transform=src.transform)
            data = src.read(1, window=window, boundless=True, fill_value=np.nan)
            transform = src.window_transform(window)
            crs = src.crs
    return data.astype("float32"), transform, crs


def fetch_dem(bbox: list[float]) -> tuple[np.ndarray, Any, str, str]:
    """Copernicus GLO-30 primary; NASADEM/SRTM fallback. Returns dem, transform, crs, source."""
    import planetary_computer as pc
    import rasterio
    from rasterio.merge import merge

    catalog = open_catalog()

    def _try(collection: str, asset_key: str, source_label: str):
        search = catalog.search(collections=[collection], bbox=bbox)
        items = list(search.items())
        if not items:
            return None
        datasets = []
        try:
            for it in items:
                signed = pc.sign(it)
                asset = signed.assets.get(asset_key) or signed.assets.get("data") or signed.assets.get("elevation")
                if asset is None:
                    continue
                href = asset.href
                # Open full dataset; merge will clip — for small pilot prefer windowed single tile.
                ds = rasterio.open(href)
                datasets.append(ds)
            if not datasets:
                return None
            if len(datasets) == 1:
                data, transform, crs = _read_dem_window(datasets[0].name, bbox)
                for ds in datasets:
                    ds.close()
                if np.all(~np.isfinite(data)) or data.size == 0:
                    return None
                return data, transform, str(crs), source_label
            # Multi-tile mosaic then window
            mosaic, out_transform = merge(datasets, bounds=(bbox[0], bbox[1], bbox[2], bbox[3]))
            for ds in datasets:
                ds.close()
            data = mosaic[0].astype("float32")
            # merge with geographic bounds assumes EPSG:4326 for these collections
            crs = "EPSG:4326"
            return data, out_transform, crs, source_label
        except Exception as exc:
            for ds in datasets:
                try:
                    ds.close()
                except Exception:
                    pass
            print(f"[dem] {collection} failed: {exc}")
            return None

    primary = _try("cop-dem-glo-30", "data", SOURCE_DEM_PRIMARY)
    if primary is not None:
        return primary
    print("[dem] Copernicus GLO-30 unavailable — trying NASADEM/SRTM fallback")
    fallback = _try("nasadem", "elevation", SOURCE_DEM_FALLBACK)
    if fallback is not None:
        return fallback
    raise RuntimeError(
        f"No DEM tiles (cop-dem-glo-30 or nasadem) for bbox {bbox}. Cannot continue."
    )


def slope_aspect(dem: np.ndarray, pixel_size_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Horn-style slope (degrees) and aspect (degrees from north) via np.gradient."""
    z = np.array(dem, dtype="float32", copy=True)
    z[~np.isfinite(z)] = np.nan
    gy, gx = np.gradient(z, pixel_size_m)
    slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
    slope_deg = np.degrees(slope_rad)
    aspect_rad = np.arctan2(-gx, gy)
    aspect_deg = (np.degrees(aspect_rad) + 360) % 360
    return slope_deg, aspect_deg


def flow_accum_proxy(dem: np.ndarray) -> np.ndarray:
    """Coarse uphill-neighbor count proxy (not full D8 routing / depression fill)."""
    finite = np.where(np.isfinite(dem), dem, -1e9)
    padded = np.pad(finite, 1, mode="edge")
    accum = np.ones_like(dem, dtype="float32")
    h, w = dem.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            neighbor = padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
            accum += (neighbor > finite).astype("float32")
    return accum


def twi_from(slope_deg: np.ndarray, flow_accum: np.ndarray) -> np.ndarray:
    slope_rad = np.radians(np.clip(slope_deg, 0.5, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(flow_accum / np.tan(slope_rad))


def _signed_href(item, key: str) -> str:
    import planetary_computer as pc

    return pc.sign(item.assets[key].href)


def _read_band_window(href: str, bbox: list[float], out_shape: tuple[int, int]) -> np.ndarray:
    import rasterio
    from pyproj import Transformer
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_PROTOCOLS="https",
    ):
        with rasterio.open(href) as src:
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            left, bottom = transformer.transform(bbox[0], bbox[1])
            right, top = transformer.transform(bbox[2], bbox[3])
            window = from_bounds(left, bottom, right, top, transform=src.transform)
            data = src.read(
                1,
                window=window,
                out_shape=out_shape,
                resampling=Resampling.bilinear,
                boundless=True,
                fill_value=0,
            )
    return data.astype("float32")


def fetch_ndmi_scl(
    bbox: list[float], date_range: str, out_shape: tuple[int, int]
) -> tuple[np.ndarray | None, dict[str, Any]]:
    """
    Best (lowest cloud) S2 L2A scene in range; NDMI with SCL clear-mask.
    Returns (ndmi_or_None, info). None + status insufficient_clear_data on fail.
    Never fabricates NDMI.
    """
    import planetary_computer as pc

    catalog = open_catalog()
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": CLOUD_LT}},
        max_items=50,
    )
    items = sorted(search.items(), key=lambda it: it.properties.get("eo:cloud_cover", 100))
    info: dict[str, Any] = {
        "date_range": date_range,
        "n_candidates": len(items),
        "status": None,
    }
    if not items:
        info["status"] = "insufficient_clear_data"
        info["reason"] = f"No S2 L2A scenes with eo:cloud_cover < {CLOUD_LT} in {date_range}"
        return None, info

    item = items[0]
    info["product_id"] = item.id
    info["date"] = item.datetime.date().isoformat() if item.datetime else None
    info["cloud_cover"] = item.properties.get("eo:cloud_cover")
    info["tile"] = item.properties.get("s2:mgrs_tile")

    try:
        b08 = _read_band_window(_signed_href(item, "B08"), bbox, out_shape) / SCALE
        b11 = _read_band_window(_signed_href(item, "B11"), bbox, out_shape) / SCALE
        scl = _read_band_window(_signed_href(item, "SCL"), bbox, out_shape)
    except Exception as exc:
        info["status"] = "insufficient_clear_data"
        info["reason"] = f"Band read failed: {exc}"
        return None, info

    scl_i = np.rint(scl).astype("int16")
    clear = np.isin(scl_i, list(SCL_CLEAR))
    clear_frac = float(np.mean(clear)) if clear.size else 0.0
    info["clear_frac"] = round(clear_frac, 4)

    if clear_frac < MIN_CLEAR_FRAC:
        info["status"] = "insufficient_clear_data"
        info["reason"] = (
            f"SCL clear fraction {clear_frac:.3f} < minimum {MIN_CLEAR_FRAC} "
            f"(fail-honest; no fabricated NDMI)"
        )
        return None, info

    denom = b08 + b11
    ndmi = np.full(out_shape, np.nan, dtype="float32")
    valid = clear & (denom != 0)
    ndmi[valid] = (b08[valid] - b11[valid]) / denom[valid]
    info["status"] = "ok"
    return ndmi, info


def cell_half_deg(lat: float, cell_m: float) -> tuple[float, float]:
    """Approximate half-cell size in degrees at latitude."""
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * max(0.2, math.cos(math.radians(lat)))
    return (cell_m / 2.0) / m_per_deg_lon, (cell_m / 2.0) / m_per_deg_lat


def assert_no_forbidden(props: dict[str, Any]) -> None:
    bad = FORBIDDEN_PROP_KEYS.intersection(props.keys())
    if bad:
        raise RuntimeError(f"Forbidden properties in output: {sorted(bad)}")


def stop_with_status(status: str, message: str, extra: dict | None = None) -> int:
    write_json(SCHEMA_PATH, schema_doc())
    payload = {
        "type": "FeatureCollection",
        "generated_at": utc_now(),
        "pilot_bbox": PILOT_BBOX,
        "status": status,
        "layer": "mountain_pilot",
        "dem_source": (extra or {}).get("dem_source"),
        "bbox_note": BBOX_LOCK_NOTE,
        "message": message,
        "features": [],
    }
    if extra:
        payload["diagnostics"] = {k: v for k, v in extra.items() if k != "dem_source"}
    write_json(GEOJSON_PATH, payload)
    meta = {
        "generated_at": utc_now(),
        "status": status,
        "layer": "mountain_pilot",
        "pilot_bbox": PILOT_BBOX,
        "message": message,
        **(extra or {}),
    }
    write_json(META_PATH, meta)
    print(f"[stop] status={status}: {message}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Round-4 mountain pilot (raw grid only)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write schema + empty stub without Planetary Computer access",
    )
    parser.add_argument(
        "--pre-range",
        default="2026-05-01/2026-05-31",
        help="Pre-khareef NDMI datetime range",
    )
    parser.add_argument(
        "--post-range",
        default="2026-09-15/2026-10-31",
        help="Post-khareef NDMI datetime range (late Sep–Oct; prior Sep 1–8 failed SCL clear)",
    )
    parser.add_argument(
        "--grid-m",
        type=float,
        default=GRID_CELL_M_DEFAULT,
        help=f"Output cell size in meters (default {GRID_CELL_M_DEFAULT})",
    )
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(SCHEMA_PATH, schema_doc())

    if args.dry_run:
        return dry_run()

    print(f"[{utc_now()}] mountain pilot bbox={PILOT_BBOX}")
    print(f"  {BBOX_LOCK_NOTE}")

    try:
        dem, transform, crs, dem_source = fetch_dem(PILOT_BBOX)
    except Exception as exc:
        return stop_with_status(
            "insufficient_clear_data",
            f"DEM fetch failed: {exc}",
            {"dem_source": None},
        )

    # Pixel size: COP-DEM is ~1 arc-sec (~30 m). transform.a in degrees when geographic.
    mid_lat = (PILOT_BBOX[1] + PILOT_BBOX[3]) / 2.0
    if abs(transform.a) < 1.0:  # degrees
        pixel_size_m = abs(transform.a) * 111_320.0 * math.cos(math.radians(mid_lat))
    else:
        pixel_size_m = abs(transform.a)

    print(f"[dem] source={dem_source}; shape={dem.shape}; px≈{pixel_size_m:.1f}m; crs={crs}")

    elev_finite = dem[np.isfinite(dem)]
    if elev_finite.size == 0:
        return stop_with_status(
            "insufficient_clear_data",
            "DEM window has no finite elevation values",
            {"dem_source": dem_source},
        )

    slope_deg, aspect_deg = slope_aspect(dem, pixel_size_m)
    flow = flow_accum_proxy(dem)
    twi_arr = twi_from(slope_deg, flow)

    slope_finite = slope_deg[np.isfinite(slope_deg)]
    p90 = float(np.nanpercentile(slope_finite, 90)) if slope_finite.size else 0.0
    print(f"[terrain] elev mean={float(np.nanmean(elev_finite)):.1f} m; slope p90={p90:.2f}°")

    if p90 < FLAT_SLOPE_P90_DEG:
        return stop_with_status(
            "flat_or_arid_stop",
            (
                f"Window appears flat (slope p90={p90:.2f}° < {FLAT_SLOPE_P90_DEG}°). "
                "Stopping — not a fog-escarpment pilot candidate. Report for DEM visual check."
            ),
            {"dem_source": dem_source, "slope_p90_deg": p90},
        )

    # NDMI shape aligned to a modest grid for moisture sampling
    out_shape = (200, 200)
    print(f"fetching pre-khareef NDMI ({args.pre_range}) with SCL...")
    ndmi_pre, pre_info = fetch_ndmi_scl(PILOT_BBOX, args.pre_range, out_shape)
    print(f"  pre: {pre_info}")
    print(f"fetching post-khareef NDMI ({args.post_range}) with SCL...")
    ndmi_post, post_info = fetch_ndmi_scl(PILOT_BBOX, args.post_range, out_shape)
    print(f"  post: {post_info}")

    if ndmi_pre is None and ndmi_post is None:
        return stop_with_status(
            "insufficient_clear_data",
            (
                "Insufficient clear Sentinel-2 data for both pre- and post-khareef windows "
                "(SCL fail-honest). No fabricated NDMI written."
            ),
            {
                "dem_source": dem_source,
                "ndmi_pre": pre_info,
                "ndmi_post": post_info,
            },
        )

    # Build coarse cell grid from DEM
    import rasterio
    from shapely.geometry import box, mapping

    h, w = dem.shape
    grid_cell_m = float(args.grid_m)
    step = max(1, int(round(grid_cell_m / max(pixel_size_m, 1.0))))
    features: list[dict[str, Any]] = []
    source_str = f"{dem_source}; {SOURCE_S2}"

    for r in range(0, h, step):
        for c in range(0, w, step):
            block_elev = dem[r : r + step, c : c + step]
            if not np.any(np.isfinite(block_elev)):
                continue
            # Cell center in DEM CRS (typically lon/lat for COP-DEM)
            row_c = r + min(step, block_elev.shape[0]) / 2.0
            col_c = c + min(step, block_elev.shape[1]) / 2.0
            lon, lat = rasterio.transform.xy(transform, row_c, col_c)
            half_lon, half_lat = cell_half_deg(float(lat), grid_cell_m)

            props: dict[str, Any] = {
                "elevation_m": round(float(np.nanmean(block_elev)), 1),
                "slope_deg": round(
                    float(np.nanmean(slope_deg[r : r + step, c : c + step])), 2
                ),
                "aspect_deg": round(
                    float(np.nanmean(aspect_deg[r : r + step, c : c + step])), 1
                ),
                "twi": round(float(np.nanmean(twi_arr[r : r + step, c : c + step])), 3),
                "status": "pilot_unverified",
                "layer": "mountain_pilot",
                "source": source_str,
                "note": (
                    "Raw terrain/moisture measurements only. No suitability, action ladder, "
                    "species, or live MPI class — science lock until spot-check."
                ),
            }

            # Map DEM row/col into NDMI out_shape indices
            if ndmi_pre is not None:
                pr = min(int(r / h * out_shape[0]), out_shape[0] - 1)
                pc_ = min(int(c / w * out_shape[1]), out_shape[1] - 1)
                val = float(ndmi_pre[pr, pc_])
                if np.isfinite(val):
                    props["ndmi_pre_khareef"] = round(val, 4)
                if pre_info.get("clear_frac") is not None:
                    props["clear_frac"] = pre_info["clear_frac"]
            if ndmi_post is not None:
                pr = min(int(r / h * out_shape[0]), out_shape[0] - 1)
                pc_ = min(int(c / w * out_shape[1]), out_shape[1] - 1)
                val = float(ndmi_post[pr, pc_])
                if np.isfinite(val):
                    props["ndmi_post_khareef"] = round(val, 4)
                if "clear_frac" not in props and post_info.get("clear_frac") is not None:
                    props["clear_frac"] = post_info["clear_frac"]
            if "ndmi_pre_khareef" in props and "ndmi_post_khareef" in props:
                props["ndmi_delta"] = round(
                    props["ndmi_post_khareef"] - props["ndmi_pre_khareef"], 4
                )

            assert_no_forbidden(props)
            features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(
                        box(lon - half_lon, lat - half_lat, lon + half_lon, lat + half_lat)
                    ),
                    "properties": props,
                }
            )

    if not features:
        return stop_with_status(
            "insufficient_clear_data",
            "No finite DEM cells to emit — empty pilot grid",
            {"dem_source": dem_source},
        )

    fc = {
        "type": "FeatureCollection",
        "generated_at": utc_now(),
        "pilot_bbox": PILOT_BBOX,
        "status": "pilot_unverified",
        "layer": "mountain_pilot",
        "dem_source": dem_source,
        "bbox_note": BBOX_LOCK_NOTE,
        "ndmi_pre": pre_info,
        "ndmi_post": post_info,
        "grid_cell_m": grid_cell_m,
        "n_features": len(features),
        "features": features,
    }
    write_json(GEOJSON_PATH, fc)

    # Compact stratified sample for git / science skim (not first-N high-elev)
    sample_path = OUT_DIR / "pilot_terrain.sample.geojson"
    try:
        from engines.mpi import stratified_sample_indices, assert_no_forbidden_partner_keys
        elevs = np.array([f["properties"].get("elevation_m", np.nan) for f in features], dtype="float64")
        slopes = np.array([f["properties"].get("slope_deg", np.nan) for f in features], dtype="float64")
        idxs = stratified_sample_indices(elevs, slopes, n_total=48)
        sample_feats = []
        fe = elevs[np.isfinite(elevs)]
        fs = slopes[np.isfinite(slopes)]
        elev_edges = np.quantile(fe, [0, 1 / 3, 2 / 3, 1]) if fe.size else [0, 0, 0, 0]
        slope_med = float(np.median(fs)) if fs.size else 0.0
        for i in idxs:
            feat = json.loads(json.dumps(features[i]))  # deep copy
            e = feat["properties"].get("elevation_m")
            s = feat["properties"].get("slope_deg")
            if e is not None and s is not None:
                if e <= elev_edges[1]:
                    eband = "low_elev"
                elif e <= elev_edges[2]:
                    eband = "mid_elev"
                else:
                    eband = "high_elev"
                feat["properties"]["sample_stratum"] = f"{eband}_{'gentle' if s < slope_med else 'steep'}"
                feat["properties"]["sample_method"] = "stratified_elev_tertile_x_slope_median"
            assert_no_forbidden_partner_keys(feat["properties"])
            sample_feats.append(feat)
        sample = {k: v for k, v in fc.items() if k != "features"}
        sample["features"] = sample_feats
        sample["sample_method"] = "stratified_elev_tertile_x_slope_median"
        sample["n_sample"] = len(sample_feats)
        sample["elev_tertile_edges_m"] = [round(float(x), 1) for x in elev_edges]
        sample["slope_median_deg"] = round(slope_med, 2)
        sample["note_sample"] = (
            "Stratified sample (low/mid/high elev × gentle/steep) — not first-N. "
            "Full grid: pilot_terrain.geojson (often gitignored)."
        )
    except Exception as exc:
        print(f"[warn] stratified sample fallback to first-48: {exc}")
        sample = {k: v for k, v in fc.items() if k != "features"}
        sample["features"] = fc["features"][:48]
        sample["note_sample"] = "Fallback first-48 — stratified helper unavailable."
    write_json(sample_path, sample)

    meta = {
        "generated_at": utc_now(),
        "status": "pilot_unverified",
        "layer": "mountain_pilot",
        "pilot_bbox": PILOT_BBOX,
        "bbox_note": BBOX_LOCK_NOTE,
        "dem_source": dem_source,
        "slope_p90_deg": p90,
        "n_features": len(features),
        "ndmi_pre": pre_info,
        "ndmi_post": post_info,
        "artifacts": {
            "geojson": str(GEOJSON_PATH.relative_to(REPO_ROOT)),
            "sample": str((OUT_DIR / "pilot_terrain.sample.geojson").relative_to(REPO_ROOT)),
            "schema": str(SCHEMA_PATH.relative_to(REPO_ROOT)),
        },
        "ui_wire": False,
        "forbidden_fields_enforced": sorted(FORBIDDEN_PROP_KEYS),
    }
    write_json(META_PATH, meta)
    print(f"wrote {len(features)} cells → {GEOJSON_PATH}")
    print(f"meta → {META_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
