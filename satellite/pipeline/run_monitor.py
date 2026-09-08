#!/usr/bin/env python3
"""
Najd (Dhofar, Oman) desert-farm satellite monitoring — first slice.

Queries Microsoft Planetary Computer STAC for Sentinel-2 L2A,
windowed-reads B04/B08/B11/(SCL) COGs, computes NDVI/NDMI on a coarse
grid, classifies early-intervention alerts, and writes app data files.

Source: Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

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
WINDOW_BBOX = [53.70, 17.90, 53.95, 18.15]  # ~0.25° x 0.25°
PRIORITY_TILES = {"39QZV", "39QYA", "39QZA", "39QYV"}
CLOUD_LT = 10.0
BARE_NDVI = 0.18
GRID_M = 500.0  # ~500 m cells
SCALE = 10000.0  # Sentinel-2 L2A reflectance scale
SOURCE_STR = "Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer"
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
TARGET_DATES_HINT = 4  # aim for 2–4 dates spanning weeks


def open_catalog():
    return Client.open(STAC_URL, modifier=pc.sign_inplace)


def search_items(catalog, datetime_range: str = "2026-06-01/2026-09-08"):
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


def compute_indices(b04, b08, b11, scl=None):
    b04f = b04.astype(np.float32) / SCALE
    b08f = b08.astype(np.float32) / SCALE
    b11f = b11.astype(np.float32) / SCALE
    # valid reflectance pixels (non-zero / reasonable)
    valid = (b04 > 0) & (b08 > 0) & (b11 > 0) & (b04 < 10000) & (b08 < 10000) & (b11 < 10000)
    if scl is not None:
        # SCL: 4=vegetation, 5=not_vegetated, 6=water, 7=unclassified,
        # 2=dark, 3=cloud_shadow; exclude clouds/cirrus/snow/nodata
        # Keep: 4,5,6,7,2,3,11? — exclude 0 nodata, 1 saturated, 8 cloud med,
        # 9 cloud high, 10 thin cirrus
        cloudlike = np.isin(scl, [0, 1, 8, 9, 10])
        valid = valid & (~cloudlike)

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


def build_grid_cells(ndvi, ndmi, valid, transform, crs, meta: dict) -> list[dict]:
    """Aggregate to ~GRID_M cells in projected CRS meters."""
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
                        "pixel_count": count,
                        "alert": "pending",
                        "date": meta["date"],
                        "source": SOURCE_STR,
                        "product_id": meta["product_id"],
                        "tile": meta["tile"],
                        "cloud_cover": meta.get("cloud_cover"),
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
    href_scl = signed_href(item, "SCL") if "SCL" in item.assets else None

    # Read B08 at native 10m for reference shape; B11 is 20m — resample to B08
    b08, transform, crs = read_window_band(href_b08, WINDOW_BBOX)
    out_shape = b08.shape
    b04, _, _ = read_window_band(href_b04, WINDOW_BBOX, out_shape=out_shape)
    b11, _, _ = read_window_band(href_b11, WINDOW_BBOX, out_shape=out_shape)
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

    ndvi, ndmi, valid = compute_indices(b04, b08, b11, scl)

    finite = np.isfinite(ndvi) & valid
    stats = {
        "date": d,
        "product_id": product_id,
        "tile": tile,
        "cloud_cover": cloud,
        "pixels_valid": int(np.sum(finite)),
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
    features = build_grid_cells(ndvi, ndmi, valid, transform, crs, meta)
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

    print("Opening Planetary Computer STAC…")
    catalog = open_catalog()
    print("Searching sentinel-2-l2a…")
    items = search_items(catalog)
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
            timeseries.append(
                {
                    "date": stats["date"],
                    "source": SOURCE_STR,
                    "product_id": stats["product_id"],
                    "tile": stats["tile"],
                    "cloud_cover": stats["cloud_cover"],
                    "window_bbox": WINDOW_BBOX,
                    "aoi_bbox": AOI_BBOX,
                    "pixels_valid": stats["pixels_valid"],
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

    # Use latest date features for latest_alerts.geojson
    latest_date = max(f["properties"]["date"] for f in all_features)
    latest_feats = [f for f in all_features if f["properties"]["date"] == latest_date]
    latest_feats = classify_alerts(latest_feats)

    # Also classify all for optional multi-date use in timeseries rollup
    all_classified = classify_alerts(all_features)

    alert_counts = defaultdict(int)
    for f in latest_feats:
        alert_counts[f["properties"]["alert"]] += 1

    geojson = {
        "type": "FeatureCollection",
        "name": "najd_latest_alerts",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "properties": {
            "source": SOURCE_STR,
            "date": latest_date,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "window_bbox": WINDOW_BBOX,
            "aoi_bbox": AOI_BBOX,
            "bare_ndvi_threshold": BARE_NDVI,
            "grid_m": GRID_M,
            "alert_counts": dict(alert_counts),
            "note": (
                "Alerts are relative early-intervention flags among vegetated "
                "cells, not definitive diagnoses."
            ),
        },
        "features": latest_feats,
    }
    GEOJSON_PATH.write_text(json.dumps(geojson))
    print(f"Wrote {GEOJSON_PATH} ({len(latest_feats)} features, date={latest_date})")

    # Enrich timeseries with alert counts per date from all_classified
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

    ts_doc = {
        "source": SOURCE_STR,
        "generated_on": datetime.now(timezone.utc).date().isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "aoi_bbox": AOI_BBOX,
        "window_bbox": WINDOW_BBOX,
        "priority_tiles": sorted(PRIORITY_TILES),
        "method": {
            "indices": ["NDVI=(B08-B04)/(B08+B04)", "NDMI=(B08-B11)/(B08+B11)"],
            "reflectance_scale": SCALE,
            "grid_m": GRID_M,
            "bare_ndvi_threshold": BARE_NDVI,
            "cloud_filter": f"eo:cloud_cover < {CLOUD_LT}",
            "stac": STAC_URL,
            "collection": "sentinel-2-l2a",
        },
        "citation": (
            "Copernicus Sentinel-2 L2A (ESA) accessed via Microsoft Planetary "
            "Computer STAC API and signed COG assets."
        ),
        "errors": errors,
        "dates": timeseries,
    }
    TIMESERIES_PATH.write_text(json.dumps(ts_doc, indent=2))
    print(f"Wrote {TIMESERIES_PATH} ({len(timeseries)} dates)")

    meta_dir = OUT_DATA / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    refresh_doc = {
        "last_updated": ts_doc["last_updated"],
        "source": "run_monitor",
        "artifacts": ["latest_alerts.geojson", "timeseries.json"],
        "generated_on": ts_doc.get("generated_on"),
    }
    refresh_path = meta_dir / "last_refresh.json"
    refresh_path.write_text(json.dumps(refresh_doc, indent=2))
    print(f"Wrote {refresh_path}")

    # Summary print
    print("\n=== ALERT COUNTS (latest date {}) ===".format(latest_date))
    for k in sorted(alert_counts.keys()):
        print(f"  {k}: {alert_counts[k]}")
    print(f"  TOTAL: {sum(alert_counts.values())}")

    # Persist run summary for RUN_NOTES
    summary = {
        "latest_date": latest_date,
        "alert_counts": dict(alert_counts),
        "timeseries_dates": [t["date"] for t in timeseries],
        "sample_stats": timeseries,
        "errors": errors,
        "window_bbox": WINDOW_BBOX,
        "n_latest_features": len(latest_feats),
    }
    (PIPELINE_DIR / "_run_summary.json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
