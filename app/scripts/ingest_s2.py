#!/usr/bin/env python3
from __future__ import annotations
import json, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import planetary_computer as pc
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from rasterio.transform import from_bounds as transform_from_bounds
from pystac_client import Client
from shapely.geometry import box, mapping

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "data"
OUT.mkdir(parents=True, exist_ok=True)
AOI = [53.4, 17.5, 54.3, 18.5]
PRIORITY_TILES = {"39QZV", "39QYA", "39QZA", "39QYV"}
GRID_STEP = 0.025
SOURCE_CITATION = {
    "provider": "ESA / Copernicus",
    "collection": "Sentinel-2 L2A",
    "access": "Microsoft Planetary Computer STAC",
    "stac": "https://planetarycomputer.microsoft.com/api/stac/v1",
    "license_note": "Contains modified Copernicus Sentinel data",
}

def search_items(limit_per_window=20):
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    windows = [
        ("recent", "2026-06-01/2026-09-08"),
        ("wheat_peak", "2026-02-01/2026-04-15"),
    ]
    picked, seen = [], set()
    for label, dt in windows:
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=AOI,
            datetime=dt,
            query={"eo:cloud_cover": {"lt": 10}},
            max_items=limit_per_window,
        )
        items = list(search.items())
        items.sort(key=lambda it: (
            0 if (it.properties.get("s2:mgrs_tile") in PRIORITY_TILES) else 1,
            it.properties.get("eo:cloud_cover", 99),
            -(it.datetime.timestamp() if it.datetime else 0),
        ))
        count = 0
        for it in items:
            tile = it.properties.get("s2:mgrs_tile")
            if tile not in PRIORITY_TILES:
                continue
            key = (label, tile)
            if key in seen:
                continue
            seen.add(key)
            picked.append((label, it))
            count += 1
            if count >= 2:
                break
    return picked

def read_band_window(url, bbox, out_shape=None):
    signed = pc.sign(url)
    with rasterio.open(signed) as src:
        window = from_bounds(bbox[0], bbox[1], bbox[2], bbox[3], transform=src.transform)
        window = window.round_offsets().round_lengths()
        data = src.read(
            1,
            window=window,
            out_shape=out_shape,
            resampling=Resampling.bilinear,
            boundless=True,
            fill_value=0,
        )
        if out_shape is not None:
            transform = transform_from_bounds(bbox[0], bbox[1], bbox[2], bbox[3], out_shape[1], out_shape[0])
        else:
            transform = src.window_transform(window)
        return data.astype("float32"), transform, src.crs


def scl_mask(scl):
    bad = np.isin(scl, [0, 1, 2, 3, 8, 9, 10, 11])
    return ~bad


def compute_indices(item, bbox):
    assets = item.assets
    b11_url = assets["B11"].href
    with rasterio.open(pc.sign(b11_url)) as src:
        window = from_bounds(bbox[0], bbox[1], bbox[2], bbox[3], transform=src.transform)
        window = window.round_offsets().round_lengths()
        h, w = int(window.height), int(window.width)
        max_side = 1024
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            h = max(32, int(h * scale))
            w = max(32, int(w * scale))
        out_shape = (h, w)
    b04, transform, crs = read_band_window(assets["B04"].href, bbox, out_shape=out_shape)
    b08, _, _ = read_band_window(assets["B08"].href, bbox, out_shape=out_shape)
    b11, _, _ = read_band_window(assets["B11"].href, bbox, out_shape=out_shape)
    scl, _, _ = read_band_window(assets["SCL"].href, bbox, out_shape=out_shape)
    scl = scl.astype("uint8")

    def refl(a):
        x = a.astype("float32")
        x = np.where(x > 0, x / 10000.0, np.nan)
        return np.clip(x, 0, 1)

    r, nir, swir = refl(b04), refl(b08), refl(b11)
    valid = scl_mask(scl) & np.isfinite(r) & np.isfinite(nir) & np.isfinite(swir)
    ndvi = np.where(valid, (nir - r) / (nir + r + 1e-6), np.nan)
    ndmi = np.where(valid, (nir - swir) / (nir + swir + 1e-6), np.nan)
    return ndvi, ndmi, transform, crs, valid

def grid_zones(ndvi, ndmi, transform, valid):
    h, w = ndvi.shape
    west, south, east, north = AOI
    a, b, c, d, e, f = transform.a, transform.b, transform.c, transform.d, transform.e, transform.f
    cell_stats = []
    zid = 0
    lat = south
    while lat < north - 1e-9:
        lon = west
        while lon < east - 1e-9:
            cell = box(lon, lat, min(lon + GRID_STEP, east), min(lat + GRID_STEP, north))
            cols = [int((x - c) / a) for x in (lon, min(lon + GRID_STEP, east))]
            rows = [int((y - f) / e) for y in (lat, min(lat + GRID_STEP, north))]
            r0, r1 = sorted(rows)
            c0, c1 = sorted(cols)
            r0, c0 = max(0, r0), max(0, c0)
            r1, c1 = min(h, r1 + 1), min(w, c1 + 1)
            lon += GRID_STEP
            if r1 <= r0 or c1 <= c0:
                continue
            patch_v = valid[r0:r1, c0:c1]
            if patch_v.size == 0 or int(patch_v.sum()) < 5:
                continue
            patch_n = ndvi[r0:r1, c0:c1]
            patch_m = ndmi[r0:r1, c0:c1]
            m_ndvi = float(np.nanmean(np.where(patch_v, patch_n, np.nan)))
            m_ndmi = float(np.nanmean(np.where(patch_v, patch_m, np.nan)))
            if not math.isfinite(m_ndvi) or not math.isfinite(m_ndmi):
                continue
            zid += 1
            cell_stats.append({
                "id": f"z{zid:04d}",
                "geometry": mapping(cell),
                "ndvi_mean": round(m_ndvi, 4),
                "ndmi_mean": round(m_ndmi, 4),
                "veg_like": m_ndvi >= 0.2,
            })
        lat += GRID_STEP

    veg = [c for c in cell_stats if c["veg_like"]]
    if len(veg) >= 3:
        ndvi_med = float(np.median([c["ndvi_mean"] for c in veg]))
        ndmi_med = float(np.median([c["ndmi_mean"] for c in veg]))
        ndvi_thr = ndvi_med - 0.12
        ndmi_thr = ndmi_med - 0.08
    else:
        ndvi_med = ndmi_med = None
        ndvi_thr, ndmi_thr = 0.25, 0.0

    features = []
    for c in cell_stats:
        alerts = []
        if c["veg_like"]:
            if c["ndmi_mean"] < ndmi_thr:
                alerts.append({
                    "type": "water",
                    "label_en": "Possible moisture / irrigation stress vs peers",
                    "label_ar": "احتمال إجهاد رطوبي / ري مقارنة بالجيران",
                })
            if c["ndvi_mean"] < ndvi_thr:
                alerts.append({
                    "type": "vigor",
                    "label_en": "Low vigor vs peers (management check — not a fertilizer lab diagnosis)",
                    "label_ar": "ضعف النمو الخضري مقارنة بالجيران (مراجعة إدارة — ليس تشخيص تسميد مخبري)",
                })
        features.append({
            "type": "Feature",
            "geometry": c["geometry"],
            "properties": {
                "id": c["id"],
                "ndvi_mean": c["ndvi_mean"],
                "ndmi_mean": c["ndmi_mean"],
                "veg_like": c["veg_like"],
                "alerts": alerts,
                "attention": len(alerts) > 0,
            },
        })
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "peer_ndvi_median": ndvi_med,
            "peer_ndmi_median": ndmi_med,
            "ndvi_alert_threshold": ndvi_thr,
            "ndmi_alert_threshold": ndmi_thr,
            "grid_step_deg": GRID_STEP,
            "veg_ndvi_floor": 0.2,
        },
    }

def summarize_raster(ndvi, ndmi, valid):
    def stats(a):
        x = a[valid]
        x = x[np.isfinite(x)]
        if x.size == 0:
            return None
        return {
            "min": round(float(np.nanmin(x)), 4),
            "p10": round(float(np.nanpercentile(x, 10)), 4),
            "p50": round(float(np.nanpercentile(x, 50)), 4),
            "p90": round(float(np.nanpercentile(x, 90)), 4),
            "max": round(float(np.nanmax(x)), 4),
            "mean": round(float(np.nanmean(x)), 4),
        }
    return {"ndvi": stats(ndvi), "ndmi": stats(ndmi), "valid_pixels": int(valid.sum())}


def main():
    print("Searching Planetary Computer STAC...")
    picked = search_items()
    if not picked:
        raise SystemExit("No clear Sentinel-2 items found")

    scenes, timeseries = [], []
    latest_alerts = latest_meta = None

    for label, item in picked:
        tile = item.properties.get("s2:mgrs_tile")
        cloud = item.properties.get("eo:cloud_cover")
        acq = item.datetime.astimezone(timezone.utc).date().isoformat() if item.datetime else None
        print(f"Processing {label} {tile} {acq} cloud={cloud} id={item.id}")
        ndvi, ndmi, transform, crs, valid = compute_indices(item, AOI)
        summary = summarize_raster(ndvi, ndmi, valid)
        alerts = grid_zones(ndvi, ndmi, transform, valid)
        scene = {
            "id": item.id,
            "window": label,
            "tile": tile,
            "acquisition_date": acq,
            "cloud_cover_percent": cloud,
            "bbox": AOI,
            "crs": str(crs) if crs else "EPSG:4326",
            "source": {
                **SOURCE_CITATION,
                "product_id": item.id,
                "mgrs_tile": tile,
                "platform": item.properties.get("platform"),
            },
            "indices": ["NDVI", "NDMI"],
            "formulas": {
                "NDVI": "(B08 - B04) / (B08 + B04)",
                "NDMI": "(B08 - B11) / (B08 + B11)",
            },
            "summary": summary,
            "alerts_path": f"alerts_{tile}_{acq}.geojson",
            "attention_zones": sum(1 for f in alerts["features"] if f["properties"]["attention"]),
            "zone_count": len(alerts["features"]),
        }
        alerts_out = dict(alerts)
        alerts_out["properties"] = {
            **alerts.get("properties", {}),
            "scene_id": item.id,
            "acquisition_date": acq,
            "tile": tile,
            "source": scene["source"],
        }
        (OUT / scene["alerts_path"]).write_text(json.dumps(alerts_out))
        scenes.append(scene)
        timeseries.append({
            "date": acq,
            "tile": tile,
            "product_id": item.id,
            "ndvi_mean": (summary["ndvi"] or {}).get("mean"),
            "ndmi_mean": (summary["ndmi"] or {}).get("mean"),
            "attention_zones": scene["attention_zones"],
            "source": scene["source"],
        })
        if latest_alerts is None or label == "wheat_peak":
            latest_alerts, latest_meta = alerts_out, scene

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "aoi_bbox": AOI,
        "pipeline": "planetary-computer-stac + rasterio windowed COG",
        "cadence_note": "Designed for weekly re-run; S2 revisit ~5 days",
        "source_default": SOURCE_CITATION,
        "scenes": scenes,
        "primary_scene_id": latest_meta["id"] if latest_meta else None,
    }
    (OUT / "scenes_live.json").write_text(json.dumps(catalog, indent=2))
    (OUT / "timeseries.json").write_text(json.dumps({
        "aoi_bbox": AOI,
        "source_default": SOURCE_CITATION,
        "points": sorted(timeseries, key=lambda p: p["date"] or ""),
    }, indent=2))
    if latest_alerts is not None:
        (OUT / "alerts_latest.geojson").write_text(json.dumps(latest_alerts))
    if latest_meta is not None:
        (OUT / "primary_scene.json").write_text(json.dumps(latest_meta, indent=2))
    print(json.dumps({
        "scenes": len(scenes),
        "primary": latest_meta["id"] if latest_meta else None,
        "attention_zones": latest_meta["attention_zones"] if latest_meta else None,
        "zone_count": latest_meta["zone_count"] if latest_meta else None,
    }, indent=2))


if __name__ == "__main__":
    main()
