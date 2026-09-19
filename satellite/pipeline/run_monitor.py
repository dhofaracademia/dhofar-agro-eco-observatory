#!/usr/bin/env python3
"""
Najd (Dhofar, Oman) desert-farm satellite monitoring — first slice.

Queries Microsoft Planetary Computer STAC for Sentinel-2 L2A,
windowed-reads B04/B08/B11/B12/(B05|B06|B07)/SCL COGs, computes NDVI/NDMI/NDRE
on a coarse grid, classifies alerts, then optionally runs Phase-1 AgProb/AOU
engines (see run_ag_probability.py; SCIENCE_LOCKS_v0.4_phase1_2.md).

Source: Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import os
import shutil
import tempfile
import uuid

import numpy as np
import planetary_computer as pc
import rasterio
from pystac_client import Client
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from shapely.geometry import box, mapping

# ---------------------------------------------------------------------------
# Paths & AOI
# ---------------------------------------------------------------------------
PIPELINE_DIR = Path(__file__).resolve().parent
CACHE_DIR = PIPELINE_DIR / "cache"
REPO_ROOT = PIPELINE_DIR.parents[1]  # .../satellite/pipeline -> repo root
OUT_DATA = Path(__import__("os").environ.get("MONITOR_OUT_DATA", str(REPO_ROOT / "app" / "public" / "data")))
GEOJSON_PATH = OUT_DATA / "latest_alerts.geojson"
TIMESERIES_PATH = OUT_DATA / "timeseries.json"

AOI_BBOX = [53.4, 17.5, 54.3, 18.5]  # full AOI (w,s,e,n)
# Manageable farm-corridor window centered near 18.0N 53.8E
WINDOW_BBOX = [53.70, 17.90, 53.98, 18.15]  # ~0.28° x 0.25°
# NOTE (fixed): east edge widened from 53.95 -> 53.98 so the Hanfit hub
# (lon 53.9667, see app/src/data/hubs.json) actually falls inside the
# monitored window instead of sitting ~0.017deg outside it. Thumrait,
# Ash Shisr, Saih Al-Khairat, and Al-Mazyunah are still NOT covered by this
# single window -- see hubs.json's covered_by_current_window flag. Extending
# coverage to those requires either enlarging WINDOW_BBOX (more compute/cost)
# or running the pipeline per-hub with a small window around each hub
# individually; the latter is the recommended next step, not a blanket
# expansion.
PRIORITY_TILES = {"39QZV", "39QYA", "39QZA", "39QYV"}
CLOUD_LT = 10.0
BARE_NDVI = 0.18
GRID_M = 500.0  # ~500 m cells
SCALE = 10000.0  # Sentinel-2 L2A reflectance scale
SOURCE_STR = "Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer"
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
TARGET_DATES_HINT = 4  # aim for 2–4 dates spanning weeks
# Clear-pixel / coverage gate — independent of scene cloud % (integrity pack P1)
MIN_CLEAR_PIXELS = int(os.environ.get("MONITOR_MIN_CLEAR_PIXELS", "500"))
MIN_CLEAR_FRACTION = float(os.environ.get("MONITOR_MIN_CLEAR_FRACTION", "0.02"))
# STAC window: default end=now (UTC), lookback configurable; fixed only when stamped
DEFAULT_LOOKBACK_DAYS = int(os.environ.get("MONITOR_STAC_LOOKBACK_DAYS", "90"))


def stac_datetime_range() -> tuple[str, dict]:
    """Return (datetime_range, window_meta). end=now unless reproducibility_fixed."""
    mode = os.environ.get("MONITOR_WINDOW_MODE", "live").strip().lower()
    if mode == "reproducibility_fixed":
        start = os.environ.get("MONITOR_STAC_START", "2026-06-01")
        end = os.environ.get("MONITOR_STAC_END", "2026-09-08")
        meta = {
            "window_mode": "reproducibility_fixed",
            "stac_start": start,
            "stac_end": end,
            "lookback_days": None,
        }
        return f"{start}/{end}", meta
    end = os.environ.get("MONITOR_STAC_END")
    if end:
        end_d = date.fromisoformat(end)
    else:
        end_d = datetime.now(timezone.utc).date()
    lookback = int(os.environ.get("MONITOR_STAC_LOOKBACK_DAYS", str(DEFAULT_LOOKBACK_DAYS)))
    start_d = end_d - timedelta(days=lookback)
    meta = {
        "window_mode": "live",
        "stac_start": start_d.isoformat(),
        "stac_end": end_d.isoformat(),
        "lookback_days": lookback,
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
    }
    return f"{start_d.isoformat()}/{end_d.isoformat()}", meta


def open_catalog():
    return Client.open(STAC_URL, modifier=pc.sign_inplace)


def search_items(catalog, datetime_range: str):
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=AOI_BBOX,
        datetime=datetime_range,
        query={"eo:cloud_cover": {"lt": CLOUD_LT}},
        max_items=200,
    )
    return list(search.items())


def pick_dates_and_items(items: list) -> dict[str, list]:
    """Select 2–4 dates spanning ~2–4 weeks; prefer priority tiles covering WINDOW."""
    by_date: dict[str, list] = defaultdict(list)
    for it in items:
        tile = it.properties.get("s2:mgrs_tile")
        if tile not in PRIORITY_TILES:
            continue
        # keep only items that intersect the analysis window
        geom = it.geometry
        if geom is None:
            continue
        from shapely.geometry import shape

        if not shape(geom).intersects(box(*WINDOW_BBOX)):
            continue
        d = it.datetime.date().isoformat()
        by_date[d].append(it)

    dates = sorted(by_date.keys(), reverse=True)
    if not dates:
        return {}

    # Prefer spread: latest, then ~1 week earlier, ~2 weeks, ~3–4 weeks
    selected: list[str] = [dates[0]]
    targets_days = [7, 14, 21, 28]
    for offset in targets_days:
        if len(selected) >= TARGET_DATES_HINT:
            break
        ref = date.fromisoformat(selected[0])
        best = None
        best_diff = 999
        for d in dates:
            if d in selected:
                continue
            diff = abs((ref - date.fromisoformat(d)).days - offset)
            if diff < best_diff:
                best_diff = diff
                best = d
        if best is not None and best_diff <= 5:
            selected.append(best)

    # fallback: take up to 4 most recent distinct dates
    if len(selected) < 2:
        selected = dates[: min(4, len(dates))]

    selected = sorted(set(selected))
    return {d: by_date[d] for d in selected}


def signed_href(item, asset_key: str) -> str:
    asset = item.assets[asset_key]
    return pc.sign(asset.href)


def read_window_band(href: str, bbox_wgs84: list[float], out_shape=None, dst_crs=None):
    """Windowed COG read for bbox; optionally resample to out_shape/dst_crs."""
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_PROTOCOLS="https"):
        with rasterio.open(href) as src:
            transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            left, bottom = transformer.transform(bbox_wgs84[0], bbox_wgs84[1])
            right, top = transformer.transform(bbox_wgs84[2], bbox_wgs84[3])
            window = from_bounds(left, bottom, right, top, transform=src.transform)
            if out_shape is None:
                data = src.read(1, window=window, boundless=True, fill_value=0)
                transform = src.window_transform(window)
                crs = src.crs
            else:
                data = src.read(
                    1,
                    window=window,
                    out_shape=out_shape,
                    resampling=Resampling.bilinear,
                    boundless=True,
                    fill_value=0,
                )
                # rebuild transform for out_shape
                from affine import Affine

                w = window.width
                h = window.height
                scale_x = w / out_shape[1]
                scale_y = h / out_shape[0]
                base = src.window_transform(window)
                transform = Affine(
                    base.a * scale_x,
                    base.b,
                    base.c,
                    base.d,
                    base.e * scale_y,
                    base.f,
                )
                crs = src.crs
            return data, transform, crs


def scl_valid_mask(b04, b08, b11, scl=None):
    """SCL gates BEFORE indices (SCIENCE_LOCKS / AgriTech / integrity pack).

    Missing SCL → all invalid (block / unclassified). Never invent clear pixels.
    """
    valid = (b04 > 0) & (b08 > 0) & (b11 > 0) & (b04 < 10000) & (b08 < 10000) & (b11 < 10000)
    if scl is None:
        return np.zeros_like(valid, dtype=bool)
    # Exclude 0 nodata, 1 saturated, 3 cloud shadow, 8/9 cloud, 10 thin cirrus
    cloudlike = np.isin(scl, [0, 1, 3, 8, 9, 10])
    return valid & (~cloudlike)


def compute_indices(b04, b08, b11, scl=None):
    b04f = b04.astype(np.float32) / SCALE
    b08f = b08.astype(np.float32) / SCALE
    b11f = b11.astype(np.float32) / SCALE
    valid = scl_valid_mask(b04, b08, b11, scl)

    ndvi = np.full(b04.shape, np.nan, dtype=np.float32)
    ndmi = np.full(b04.shape, np.nan, dtype=np.float32)
    denom_v = b08f + b04f
    denom_m = b08f + b11f
    ok_v = valid & (np.abs(denom_v) > 1e-6)
    ok_m = valid & (np.abs(denom_m) > 1e-6)
    ndvi[ok_v] = (b08f[ok_v] - b04f[ok_v]) / denom_v[ok_v]
    ndmi[ok_m] = (b08f[ok_m] - b11f[ok_m]) / denom_m[ok_m]
    return ndvi, ndmi, valid


def pixel_to_lonlat(transform, crs, row, col):
    x, y = rasterio.transform.xy(transform, row, col, offset="center")
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lon, lat


def build_grid_cells(ndvi, ndmi, valid, transform, crs, meta: dict, ndre=None, ndre_meta=None, b11=None, b12=None) -> list[dict]:
    """Aggregate to ~GRID_M cells in projected CRS meters.

    geometry_kind=monitoring_grid_500m is the fallback/debug layer; AOU
    segments come from run_ag_probability.py (SCIENCE_LOCKS §1.4).
    """
    # estimate pixel size in meters
    px_m = abs(transform.a)
    # if CRS is UTM, a is meters; if geographic, convert roughly
    if crs and crs.is_geographic:
        # degrees -> meters approx at mid lat
        mid_lat = (WINDOW_BBOX[1] + WINDOW_BBOX[3]) / 2
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * math.cos(math.radians(mid_lat))
        px_m = abs(transform.a) * m_per_deg_lon

    block = max(1, int(round(GRID_M / max(px_m, 1.0))))
    h, w = ndvi.shape
    features = []
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    for r0 in range(0, h, block):
        for c0 in range(0, w, block):
            r1 = min(r0 + block, h)
            c1 = min(c0 + block, w)
            n_slice = ndvi[r0:r1, c0:c1]
            m_slice = ndmi[r0:r1, c0:c1]
            v_slice = valid[r0:r1, c0:c1]
            count = int(np.sum(v_slice & np.isfinite(n_slice) & np.isfinite(m_slice)))
            if count < 5:
                continue
            mask = v_slice & np.isfinite(n_slice) & np.isfinite(m_slice)
            mean_ndvi = float(np.mean(n_slice[mask]))
            mean_ndmi = float(np.mean(m_slice[mask]))
            mean_ndre = None
            ndre_available = False
            ndre_status = "unavailable"
            ndre_band = None
            if ndre is not None:
                e_slice = ndre[r0:r1, c0:c1]
                emask = mask & np.isfinite(e_slice)
                if int(np.sum(emask)) >= 5:
                    mean_ndre = float(np.mean(e_slice[emask]))
                    ndre_available = True
                    ndre_status = (ndre_meta or {}).get("ndre_status", "ok")
                    ndre_band = (ndre_meta or {}).get("ndre_band")

            # Prefer explicit B11/B12 SWIR brightness for AgProb (fallback = NDVI+NDMI proxy)
            swir_feature = None
            swir_source = "proxy_ndvi_ndmi"
            mean_b11 = mean_b12 = None
            if b11 is not None:
                s11 = b11[r0:r1, c0:c1]
                sm = mask & np.isfinite(s11) & (s11 > 0)
                if int(np.sum(sm)) >= 5:
                    mean_b11 = float(np.mean(s11[sm]))
            if b12 is not None:
                s12 = b12[r0:r1, c0:c1]
                sm = mask & np.isfinite(s12) & (s12 > 0)
                if int(np.sum(sm)) >= 5:
                    mean_b12 = float(np.mean(s12[sm]))
            if mean_b11 is not None or mean_b12 is not None:
                try:
                    from engines.ag_probability import feature_swir_from_bands
                    swir_feature = feature_swir_from_bands(mean_b11, mean_b12)
                    if swir_feature is not None:
                        swir_source = "b11_b12" if mean_b12 is not None else "b11"
                except Exception:
                    swir_feature = None

            # cell corners in pixel space -> lon/lat polygon
            xs = [c0, c1, c1, c0, c0]
            ys = [r0, r0, r1, r1, r0]
            coords = []
            for col, row in zip(xs, ys):
                x, y = rasterio.transform.xy(transform, row, col, offset="ul")
                lon, lat = transformer.transform(x, y)
                coords.append([lon, lat])

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [coords]},
                    "properties": {
                        "ndvi": round(mean_ndvi, 4),
                        "ndmi": round(mean_ndmi, 4),
                        "ndre": None if mean_ndre is None else round(mean_ndre, 4),
                        "ndre_available": ndre_available,
                        "ndre_status": ndre_status,
                        "ndre_band": ndre_band,
                        "swir_feature": None if swir_feature is None else round(float(swir_feature), 4),
                        "swir_source": swir_source,
                        "pixel_count": count,
                        "alert": "pending",
                        "date": meta["date"],
                        "source": SOURCE_STR,
                        "product_id": meta["product_id"],
                        "tile": meta["tile"],
                        "cloud_cover": meta.get("cloud_cover"),
                        "geometry_kind": "monitoring_grid_500m",
                    },
                }
            )
    return features


def classify_alerts(features: list[dict]) -> list[dict]:
    """Classify cells relative to vegetated peers on the same date."""
    by_date: dict[str, list] = defaultdict(list)
    for f in features:
        by_date[f["properties"]["date"]].append(f)

    for d, feats in by_date.items():
        veg = [
            f
            for f in feats
            if f["properties"]["ndvi"] is not None and f["properties"]["ndvi"] >= BARE_NDVI
        ]
        if len(veg) >= 5:
            ndvi_vals = np.array([f["properties"]["ndvi"] for f in veg], dtype=np.float64)
            ndmi_vals = np.array([f["properties"]["ndmi"] for f in veg], dtype=np.float64)
            ndvi_p25 = float(np.percentile(ndvi_vals, 25))
            ndmi_p25 = float(np.percentile(ndmi_vals, 25))
        else:
            ndvi_p25 = 0.25
            ndmi_p25 = 0.0

        for f in feats:
            p = f["properties"]
            ndvi = p["ndvi"]
            ndmi = p["ndmi"]
            if ndvi is None or not math.isfinite(ndvi):
                p["alert"] = "unclear"
            elif ndvi < BARE_NDVI:
                p["alert"] = "bare"
            elif ndmi < ndmi_p25 and ndvi >= BARE_NDVI:
                # water stress attention among vegetated
                p["alert"] = "water_attention"
            elif ndvi < ndvi_p25:
                p["alert"] = "vigor_attention"
            else:
                p["alert"] = "healthy"
            p["ndvi_p25_veg"] = round(ndvi_p25, 4)
            p["ndmi_p25_veg"] = round(ndmi_p25, 4)
    return features


def process_item(item) -> tuple[list[dict], dict]:
    tile = item.properties.get("s2:mgrs_tile", "?")
    d = item.datetime.date().isoformat()
    product_id = item.id
    cloud = item.properties.get("eo:cloud_cover")
    print(f"  Processing {product_id} tile={tile} date={d} cloud={cloud}")

    href_b04 = signed_href(item, "B04")
    href_b08 = signed_href(item, "B08")
    href_b11 = signed_href(item, "B11")
    href_b12 = signed_href(item, "B12") if "B12" in item.assets else None
    href_scl = signed_href(item, "SCL") if "SCL" in item.assets else None
    # Red-edge preference B05 → B06 → B07 (documented fallback only)
    href_re = None
    re_key = None
    for key in ("B05", "B06", "B07"):
        if key in item.assets:
            href_re = signed_href(item, key)
            re_key = key
            break

    # Read B08 at native 10m for reference shape; B11 is 20m — resample to B08
    b08, transform, crs = read_window_band(href_b08, WINDOW_BBOX)
    out_shape = b08.shape
    b04, _, _ = read_window_band(href_b04, WINDOW_BBOX, out_shape=out_shape)
    b11, _, _ = read_window_band(href_b11, WINDOW_BBOX, out_shape=out_shape)
    b12 = None
    if href_b12:
        try:
            b12, _, _ = read_window_band(href_b12, WINDOW_BBOX, out_shape=out_shape)
        except Exception as e:
            print(f"    B12 read failed (non-fatal): {e}")
            b12 = None
    scl = None
    if href_scl:
        try:
            scl, _, _ = read_window_band(
                href_scl, WINDOW_BBOX, out_shape=out_shape
            )
            # SCL should use nearest; re-read with nearest if we used bilinear
            with rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_PROTOCOLS="https",
            ):
                with rasterio.open(href_scl) as src:
                    transformer = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
                    left, bottom = transformer.transform(WINDOW_BBOX[0], WINDOW_BBOX[1])
                    right, top = transformer.transform(WINDOW_BBOX[2], WINDOW_BBOX[3])
                    window = from_bounds(left, bottom, right, top, transform=src.transform)
                    scl = src.read(
                        1,
                        window=window,
                        out_shape=out_shape,
                        resampling=Resampling.nearest,
                        boundless=True,
                        fill_value=0,
                    )
        except Exception as e:
            print(f"    SCL read failed: {e}")
            scl = None

    scl_missing = scl is None
    ndvi, ndmi, valid = compute_indices(b04, b08, b11, scl)
    if scl_missing:
        print("    SCL missing → blocked (unclassified); no clear pixels invented")

    # NDRE after SCL gate — SCIENCE_LOCKS / AgriTech prefs
    ndre = None
    ndre_meta = {"ndre_available": False, "ndre_band": None, "ndre_status": "unavailable"}
    try:
        from engines.ndre import compute_ndre

        b05 = b06 = b07 = None
        if href_re and re_key:
            re_band, _, _ = read_window_band(href_re, WINDOW_BBOX, out_shape=out_shape)
            if re_key == "B05":
                b05 = re_band
            elif re_key == "B06":
                b06 = re_band
            else:
                b07 = re_band
        ndre, band_used, ndre_meta = compute_ndre(
            b08, b05=b05, b06=b06, b07=b07, valid=valid
        )
        print(f"    NDRE status={ndre_meta.get('ndre_status')} band={band_used}")
    except Exception as e:
        print(f"    NDRE skipped: {e}")

    finite = np.isfinite(ndvi) & valid
    n_clear = int(np.sum(finite))
    n_total = int(ndvi.size)
    clear_fraction = (n_clear / n_total) if n_total else 0.0
    coverage_ok = (n_clear >= MIN_CLEAR_PIXELS) and (clear_fraction >= MIN_CLEAR_FRACTION)
    if not coverage_ok or scl_missing:
        print(
            f"    coverage gate FAIL clear={n_clear}/{n_total} "
            f"frac={clear_fraction:.4f} min_px={MIN_CLEAR_PIXELS} "
            f"min_frac={MIN_CLEAR_FRACTION} scl_missing={scl_missing}"
        )
        stats = {
            "date": d,
            "product_id": product_id,
            "tile": tile,
            "cloud_cover": cloud,
            "pixels_valid": n_clear,
            "clear_fraction": round(clear_fraction, 6),
            "coverage_ok": False,
            "scl_missing": scl_missing,
            "status": "insufficient_clear_data" if not scl_missing else "scl_missing_blocked",
            "scene_capture_date": d,
            "ndvi_mean": None,
            "ndvi_p10": None,
            "ndvi_p50": None,
            "ndvi_p90": None,
            "ndmi_mean": None,
            "ndmi_p10": None,
            "ndmi_p50": None,
            "ndmi_p90": None,
            "shape": list(b08.shape),
            "source": SOURCE_STR,
        }
        return [], stats

    stats = {
        "date": d,
        "product_id": product_id,
        "tile": tile,
        "cloud_cover": cloud,
        "pixels_valid": n_clear,
        "clear_fraction": round(clear_fraction, 6),
        "coverage_ok": True,
        "scl_missing": False,
        "scene_capture_date": d,
        "ndvi_mean": float(np.nanmean(ndvi[finite])) if np.any(finite) else None,
        "ndvi_p10": float(np.nanpercentile(ndvi[finite], 10)) if np.any(finite) else None,
        "ndvi_p50": float(np.nanpercentile(ndvi[finite], 50)) if np.any(finite) else None,
        "ndvi_p90": float(np.nanpercentile(ndvi[finite], 90)) if np.any(finite) else None,
        "ndmi_mean": float(np.nanmean(ndmi[finite])) if np.any(finite) else None,
        "ndmi_p10": float(np.nanpercentile(ndmi[finite], 10)) if np.any(finite) else None,
        "ndmi_p50": float(np.nanpercentile(ndmi[finite], 50)) if np.any(finite) else None,
        "ndmi_p90": float(np.nanpercentile(ndmi[finite], 90)) if np.any(finite) else None,
        "shape": list(b08.shape),
        "source": SOURCE_STR,
    }
    print(
        f"    valid={stats['pixels_valid']} "
        f"NDVI mean={stats['ndvi_mean']} p50={stats['ndvi_p50']} "
        f"NDMI mean={stats['ndmi_mean']} p50={stats['ndmi_p50']}"
    )

    meta = {
        "date": d,
        "product_id": product_id,
        "tile": tile,
        "cloud_cover": cloud,
    }
    features = build_grid_cells(
        ndvi, ndmi, valid, transform, crs, meta, ndre=ndre, ndre_meta=ndre_meta, b11=b11, b12=b12
    )
    return features, stats


def pick_best_item_per_date(items: list):
    """One item per date: prefer tile covering window center, lowest cloud."""
    # prefer 39QYA / 39QZA which cover ~53.8E 18.0N
    pref = ["39QYA", "39QZA", "39QYV", "39QZV"]

    def score(it):
        tile = it.properties.get("s2:mgrs_tile")
        try:
            rank = pref.index(tile)
        except ValueError:
            rank = 99
        cc = it.properties.get("eo:cloud_cover", 100)
        return (rank, cc)

    return sorted(items, key=score)[0]


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    reprocess_time = datetime.now(timezone.utc).isoformat()
    datetime_range, window_meta = stac_datetime_range()

    print("Opening Planetary Computer STAC…")
    catalog = open_catalog()
    print(
        f"Searching sentinel-2-l2a… window={datetime_range} "
        f"mode={window_meta.get('window_mode')} run_id={run_id}"
    )
    items = search_items(catalog, datetime_range)
    print(f"STAC returned {len(items)} items (cloud<{CLOUD_LT})")

    selected = pick_dates_and_items(items)
    if not selected:
        print("ERROR: no priority-tile items intersecting analysis window.", file=sys.stderr)
        return 1

    print("Selected dates:", sorted(selected.keys()))

    all_features: list[dict] = []
    timeseries: list[dict] = []
    errors: list[str] = []

    for d in sorted(selected.keys()):
        item = pick_best_item_per_date(selected[d])
        try:
            feats, stats = process_item(item)
            all_features.extend(feats)
            if not stats.get("coverage_ok", True) or stats.get("status") in (
                "insufficient_clear_data",
                "scl_missing_blocked",
            ):
                errors.append(
                    f"{stats.get('product_id')}: {stats.get('status', 'coverage_fail')}"
                )
                continue
            timeseries.append(
                {
                    "date": stats["date"],
                    "scene_capture_date": stats.get("scene_capture_date", stats["date"]),
                    "source": SOURCE_STR,
                    "product_id": stats["product_id"],
                    "tile": stats["tile"],
                    "cloud_cover": stats["cloud_cover"],
                    "window_bbox": WINDOW_BBOX,
                    "aoi_bbox": AOI_BBOX,
                    "pixels_valid": stats["pixels_valid"],
                    "clear_fraction": stats.get("clear_fraction"),
                    "ndvi": {
                        "mean": stats["ndvi_mean"],
                        "p10": stats["ndvi_p10"],
                        "p50": stats["ndvi_p50"],
                        "p90": stats["ndvi_p90"],
                    },
                    "ndmi": {
                        "mean": stats["ndmi_mean"],
                        "p10": stats["ndmi_p10"],
                        "p50": stats["ndmi_p50"],
                        "p90": stats["ndmi_p90"],
                    },
                    "grid_cell_count_raw": len(feats),
                    "citation": (
                        f"{SOURCE_STR}; product {stats['product_id']}; "
                        f"acquisition {stats['date']}; MGRS tile {stats['tile']}."
                    ),
                }
            )
        except Exception as e:
            msg = f"{item.id}: {type(e).__name__}: {e}"
            print(f"  FAILED: {msg}")
            errors.append(msg)

    if not all_features:
        print("ERROR: no features produced.", file=sys.stderr)
        notes = {
            "errors": errors,
            "selected_dates": list(selected.keys()),
        }
        (PIPELINE_DIR / "_partial_errors.json").write_text(json.dumps(notes, indent=2))
        return 2

    # Single classify pass for ALL dates → same classifier for map + timeseries
    all_classified = classify_alerts(all_features)
    latest_date = max(f["properties"]["date"] for f in all_classified)
    latest_feats = [f for f in all_classified if f["properties"]["date"] == latest_date]

    alert_counts = defaultdict(int)
    for f in latest_feats:
        alert_counts[f["properties"]["alert"]] += 1

    # Enrich timeseries with alert counts from the SAME classified set
    for ts in timeseries:
        d = ts["date"]
        counts = defaultdict(int)
        n = 0
        for f in all_classified:
            if f["properties"]["date"] == d:
                counts[f["properties"]["alert"]] += 1
                n += 1
        ts["alert_counts"] = dict(counts)
        ts["grid_cell_count"] = n
        ts["run_id"] = run_id
        ts["classifier"] = "classify_alerts_relative_p25"
        ts["scene_capture_date"] = d
        ts["reprocess_time_utc"] = reprocess_time

    # Consistency: latest map counts == timeseries counts for latest_date
    ts_latest = next((t for t in timeseries if t["date"] == latest_date), None)
    if ts_latest is not None:
        from engines.observation_integrity import alert_counts_match

        if not alert_counts_match(dict(alert_counts), dict(ts_latest.get("alert_counts") or {})):
            print(
                f"ERROR: monitor alert/timeseries mismatch date={latest_date} "
                f"map={dict(alert_counts)} ts={ts_latest.get('alert_counts')}",
                file=sys.stderr,
            )
            return 3

    geojson = {
        "type": "FeatureCollection",
        "name": "najd_latest_alerts",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "properties": {
            "source": SOURCE_STR,
            "date": latest_date,
            "scene_capture_date": latest_date,
            "reprocess_time_utc": reprocess_time,
            "run_id": run_id,
            "last_updated": reprocess_time,
            "window_bbox": WINDOW_BBOX,
            "aoi_bbox": AOI_BBOX,
            "bare_ndvi_threshold": BARE_NDVI,
            "grid_m": GRID_M,
            "alert_counts": dict(alert_counts),
            "stac_window": window_meta,
            "min_clear_pixels": MIN_CLEAR_PIXELS,
            "min_clear_fraction": MIN_CLEAR_FRACTION,
            "consistency_status": "ok",
            "note": (
                "Alerts are relative early-intervention flags among vegetated "
                "cells, not definitive diagnoses. scene_capture_date ≠ reprocess_time."
            ),
        },
        "features": latest_feats,
    }

    ts_doc = {
        "source": SOURCE_STR,
        "generated_on": datetime.now(timezone.utc).date().isoformat(),
        "last_updated": reprocess_time,
        "run_id": run_id,
        "reprocess_time_utc": reprocess_time,
        "aoi_bbox": AOI_BBOX,
        "window_bbox": WINDOW_BBOX,
        "priority_tiles": sorted(PRIORITY_TILES),
        "stac_window": window_meta,
        "min_clear_pixels": MIN_CLEAR_PIXELS,
        "min_clear_fraction": MIN_CLEAR_FRACTION,
        "method": {
            "indices": [
                "NDVI=(B08-B04)/(B08+B04)",
                "NDMI=(B08-B11)/(B08+B11)",
                "NDRE=(B08-B05)/(B08+B05) [B06/B07 documented fallback only]",
            ],
            "formula_ref": (
                "SCIENCE_LOCKS_v0.4_phase1_2.md + "
                "SCIENCE_LOCKS_v0.4_observation_integrity.md"
            ),
            "reflectance_scale": SCALE,
            "grid_m": GRID_M,
            "bare_ndvi_threshold": BARE_NDVI,
            "cloud_filter": f"eo:cloud_cover < {CLOUD_LT}",
            "coverage_gate": {
                "min_clear_pixels": MIN_CLEAR_PIXELS,
                "min_clear_fraction": MIN_CLEAR_FRACTION,
                "independent_of_cloud_pct": True,
                "missing_scl": "block_unclassified",
            },
            "stac": STAC_URL,
            "collection": "sentinel-2-l2a",
            "classifier": "classify_alerts_relative_p25",
        },
        "citation": (
            "Copernicus Sentinel-2 L2A (ESA) accessed via Microsoft Planetary "
            "Computer STAC API and signed COG assets."
        ),
        "errors": errors,
        "dates": timeseries,
    }

    # Cross-stage atomic publish (SCIENCE_LOCKS post-integrity §3 / Integrity deferred C):
    # Stage monitor outputs; run AOU/AgProb against the stage; promote public ONLY if AOU exits 0.
    # Forbidden: promoting latest_alerts / timeseries to public before AOU success.
    stage_root = Path(tempfile.mkdtemp(prefix=f"monitor_aou_stage_{run_id}_", dir=str(OUT_DATA)))
    try:
        # Seed stage with existing public AOU ledger/registry so AgProb can append
        import os
        for sub in ("aou", "meta", "decision"):
            src = OUT_DATA / sub
            dst = stage_root / sub
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                dst.mkdir(parents=True, exist_ok=True)

        (stage_root / "latest_alerts.geojson").write_text(json.dumps(geojson))
        (stage_root / "timeseries.json").write_text(json.dumps(ts_doc, indent=2))
        refresh_doc = {
            "last_updated": ts_doc["last_updated"],
            "source": "run_monitor",
            "run_id": run_id,
            "artifacts": ["latest_alerts.geojson", "timeseries.json"],
            "generated_on": ts_doc.get("generated_on"),
            "stac_window": window_meta,
            "scene_capture_date": latest_date,
            "reprocess_time_utc": reprocess_time,
            "mountain_seeding_hold": True,
            "publish_gate": "awaiting_aou_success",
            "coverage_gate": {
                "min_clear_pixels": MIN_CLEAR_PIXELS,
                "min_clear_fraction": MIN_CLEAR_FRACTION,
                "min_clear_pixels_cell": int(os.environ.get("MONITOR_MIN_CLEAR_PIXELS_CELL", "50")),
                "min_clear_fraction_aou": float(os.environ.get("MONITOR_MIN_CLEAR_FRACTION_AOU", "0.20")),
            },
        }
        (stage_root / "meta" / "last_refresh.json").write_text(json.dumps(refresh_doc, indent=2))
        (stage_root / "meta" / "run_meta.json").write_text(json.dumps(refresh_doc, indent=2))

        print(f"Staged monitor artifacts under {stage_root} (public untouched until AOU OK)")
        print("\n=== ALERT COUNTS (latest date {}) ===".format(latest_date))
        for k in sorted(alert_counts.keys()):
            print(f"  {k}: {alert_counts[k]}")
        print(f"  TOTAL: {sum(alert_counts.values())}")

        summary = {
            "latest_date": latest_date,
            "alert_counts": dict(alert_counts),
            "timeseries_dates": [t["date"] for t in timeseries],
            "sample_stats": timeseries,
            "errors": errors,
            "window_bbox": WINDOW_BBOX,
            "n_latest_features": len(latest_feats),
            "run_id": run_id,
            "stac_window": window_meta,
            "stage_root": str(stage_root),
        }
        (PIPELINE_DIR / "_run_summary.json").write_text(json.dumps(summary, indent=2))

        # Point AgProb at staging — not public
        prev_out = os.environ.get("MONITOR_OUT_DATA")
        os.environ["MONITOR_OUT_DATA"] = str(stage_root)
        try:
            from run_ag_probability import main as ag_main

            print("\nRunning Phase-1 Agricultural Probability / AOU engines on staging…")
            rc = ag_main()
        except Exception as e:
            print(f"ERROR: AgProb engines failed: {e}", file=sys.stderr)
            print("Keeping last-good public set; discarding stage.", file=sys.stderr)
            return 4
        finally:
            if prev_out is None:
                os.environ.pop("MONITOR_OUT_DATA", None)
            else:
                os.environ["MONITOR_OUT_DATA"] = prev_out

        if rc != 0:
            print(
                f"ERROR: run_ag_probability exited {rc} — public last-good retained; stage discarded",
                file=sys.stderr,
            )
            return rc if rc else 4

        # Decision scaffolds against the same stage (full partner release)
        try:
            from run_decision_scaffolds import main as decision_main

            print("\nRunning Phase-3 Decision scaffolds on staging…")
            drc = decision_main()
        except Exception as e:
            print(f"ERROR: Decision scaffolds failed: {e}", file=sys.stderr)
            print("Keeping last-good public set; discarding stage.", file=sys.stderr)
            return 5
        if drc != 0:
            print(
                f"ERROR: run_decision_scaffolds exited {drc} — public last-good retained; stage discarded",
                file=sys.stderr,
            )
            return drc if drc else 5

        # Full-release atomic promote (deep re-check §7): ag+obs+decision, one release_id
        promote = [
            "latest_alerts.geojson",
            "timeseries.json",
            "aou/aou_observations.json",
            "aou/aou_registry.geojson",
            "aou/aou_registry.json",
            "meta/last_refresh.json",
            "meta/run_meta.json",
            "decision/aou_suitability_components.json",
            "decision/aou_confidence.json",
            "decision/aou_evidence_gaps.json",
            "decision/action_ladder.stubs.json",
            "decision/run_meta.json",
        ]
        required = list(promote)  # missing any → hard fail, no partial swap
        missing = [rel for rel in required if not (stage_root / rel).exists()]
        if missing:
            print(
                f"ERROR: staged release missing required files {missing} — "
                "public last-good retained (all-or-nothing)",
                file=sys.stderr,
            )
            return 6

        release_id = run_id
        for meta_name in ("last_refresh.json", "run_meta.json"):
            mp = stage_root / "meta" / meta_name
            if mp.is_file():
                try:
                    doc = json.loads(mp.read_text())
                    doc["publish_gate"] = "full_release_ok"
                    doc["source"] = "run_monitor+run_ag_probability+run_decision_scaffolds"
                    doc["release_id"] = release_id
                    doc["formula_ref"] = (
                        "SCIENCE_LOCKS_v0.4_observation_integrity.md + "
                        "SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md + "
                        "SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md"
                    )
                    doc["promote_includes_decision"] = True
                    doc["mountain_seeding_hold"] = True
                    mp.write_text(json.dumps(doc, indent=2))
                except Exception:
                    pass
        # Stamp decision run_meta with same release_id
        dmeta = stage_root / "decision" / "run_meta.json"
        if dmeta.is_file():
            try:
                doc = json.loads(dmeta.read_text())
                doc["release_id"] = release_id
                doc["run_id"] = release_id
                dmeta.write_text(json.dumps(doc, indent=2))
            except Exception:
                pass

        # All-or-nothing: stage to a temp public swap dir then move — on mid-swap
        # failure we still prefer not leaving mixed versions; move file-by-file
        # only after required set verified above.
        for rel in promote:
            src = stage_root / rel
            dst = OUT_DATA / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))

        print(f"Promoted full release {release_id} → {OUT_DATA} (AOU+Decision exit 0)")
        print(f"Wrote {GEOJSON_PATH} ({len(latest_feats)} features, date={latest_date})")
        print(f"Wrote {TIMESERIES_PATH} ({len(timeseries)} dates)")
        return 0
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
