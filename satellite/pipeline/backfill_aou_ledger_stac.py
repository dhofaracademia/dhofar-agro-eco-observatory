#!/usr/bin/env python3
"""Backfill AOU temporal ledger from timeseries product dates via STAC COG samples.

Honest AOU-scoped means (series_scope=aou_direct) for dates that have a
product_id in timeseries.json but no ledger row yet. Does not invent window
means. Does not retune thresholds. Mountain hold unchanged.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import planetary_computer as pc
import rasterio
from pystac_client import Client
from rasterio.mask import mask as rio_mask
from rasterio.windows import from_bounds
from shapely.geometry import mapping, shape

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))

from engines.observation_integrity import (  # noqa: E402
    biotic_status_three_state,
    ledger_persistence_feature,
    ledger_sequence_rows,
    temporal_evidence_labels,
)
from engines.ag_probability import agricultural_probability, persistence_status  # noqa: E402

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
SOURCE_STR = "Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer"
SCALE = 10000.0
BARE_NDVI = 0.18


def out_data_dir() -> Path:
    return Path(os.environ.get("MONITOR_OUT_DATA", str(PIPELINE_DIR.parents[1] / "app" / "public" / "data")))


def open_catalog():
    return Client.open(STAC_URL, modifier=pc.sign_inplace)


def find_item(catalog, product_id: str, date: str, bbox: list[float], tile: str | None):
    # Prefer exact product id
    if product_id:
        try:
            search = catalog.search(collections=["sentinel-2-l2a"], ids=[product_id])
            items = list(search.items())
            if items:
                return items[0]
        except Exception:
            pass
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{date}/{date}",
        query={"eo:cloud_cover": {"lt": 80}},
    )
    items = list(search.items())
    for it in items:
        if product_id and it.id == product_id:
            return it
    if tile:
        for it in items:
            if tile in (it.id or "") or (it.properties or {}).get("s2:mgrs_tile") == tile:
                return it
    if not items:
        return None
    return min(items, key=lambda it: float((it.properties or {}).get("eo:cloud_cover") or 99))


def _signed(item, key: str) -> str | None:
    if key not in item.assets:
        return None
    return pc.sign(item.assets[key].href)


def sample_aou_on_item(item, geom) -> dict[str, Any] | None:
    """Mean NDVI/NDMI + clear_fraction over AOU geometry from signed COGs."""
    from pyproj import Transformer
    from shapely.ops import transform as shp_transform

    href04 = _signed(item, "B04")
    href08 = _signed(item, "B08")
    href11 = _signed(item, "B11")
    href_scl = _signed(item, "SCL")
    if not (href04 and href08 and href11):
        return None
    g = shape(geom) if not hasattr(geom, "bounds") else geom
    if g.is_empty:
        return None

    def read_band(href):
        with rasterio.open(href) as ds:
            g_use = g
            if ds.crs and str(ds.crs) not in ("EPSG:4326", "OGC:CRS84"):
                transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
                g_use = shp_transform(lambda x, y: transformer.transform(x, y), g)
            shapes = [mapping(g_use)]
            out, _ = rio_mask(ds, shapes, crop=True, filled=True, nodata=0)
            return out[0].astype(np.float32)

    try:
        b04 = read_band(href04)
        b08 = read_band(href08)
        b11 = read_band(href11)
    except Exception:
        return None
    scl = None
    if href_scl:
        try:
            scl = read_band(href_scl)
        except Exception:
            scl = None

    # Align shapes
    h = min(b04.shape[0], b08.shape[0], b11.shape[0])
    w = min(b04.shape[1], b08.shape[1], b11.shape[1])
    b04, b08, b11 = b04[:h, :w], b08[:h, :w], b11[:h, :w]
    if scl is not None:
        scl = scl[:h, :w]

    # SCL clear: 4=vegetation, 5=bare, 6=water, 7=unclassified sometimes kept out
    # Match monitor: typically clear = {4,5,6,7,11} or similar — use common S2 clear set
    if scl is not None:
        clear = np.isin(scl.astype(np.uint8), [4, 5, 6, 11])
    else:
        clear = (b04 > 0) & (b08 > 0)
    finite = np.isfinite(b04) & np.isfinite(b08) & np.isfinite(b11) & (b04 > 0) & (b08 > 0)
    valid = clear & finite
    total = int(finite.sum()) if scl is None else int(finite.sum())
    n_clear = int(valid.sum())
    if n_clear < 5:
        return None
    b04v = b04[valid] / SCALE
    b08v = b08[valid] / SCALE
    b11v = b11[valid] / SCALE
    ndvi = (b08v - b04v) / np.maximum(b08v + b04v, 1e-6)
    ndmi = (b08v - b11v) / np.maximum(b08v + b11v, 1e-6)
    clear_fraction = float(n_clear) / float(max(total, 1))
    return {
        "ndvi": float(np.mean(ndvi)),
        "ndmi": float(np.mean(ndmi)),
        "clear_fraction": round(clear_fraction, 6),
        "pixel_count": n_clear,
        "valid_pixel_count": n_clear,
        "total_pixel_count": max(total, 1),
        "clear_fraction_basis": "scl_clear_over_finite" if scl is not None else "positive_reflectance_proxy",
        "product_id": item.id,
        "tile": (item.properties or {}).get("s2:mgrs_tile"),
        "cloud_cover": (item.properties or {}).get("eo:cloud_cover"),
        "source": SOURCE_STR,
    }


def main() -> int:
    out = out_data_dir()
    ts_path = out / "timeseries.json"
    obs_path = out / "aou" / "aou_observations.json"
    reg_path = out / "aou" / "aou_registry.json"
    if not ts_path.exists() or not obs_path.exists() or not reg_path.exists():
        print("ERROR: missing timeseries/obs/registry", file=sys.stderr)
        return 1

    ts = json.loads(ts_path.read_text())
    obs = json.loads(obs_path.read_text())
    reg = json.loads(reg_path.read_text())
    dates = ts.get("dates") or []
    if len(dates) < 2:
        print("No multi-date timeseries to backfill")
        return 0

    # AOU geometries from registry
    aou_geoms: dict[str, Any] = {}
    for u in reg.get("units") or []:
        aid = u.get("aou_id")
        g = u.get("geometry")
        if aid and g:
            aou_geoms[aid] = g
    if not aou_geoms:
        # try geojson
        gj = out / "aou" / "aou_registry.geojson"
        if gj.exists():
            fc = json.loads(gj.read_text())
            for f in fc.get("features") or []:
                aid = (f.get("properties") or {}).get("aou_id")
                if aid and f.get("geometry"):
                    aou_geoms[aid] = f["geometry"]
    if not aou_geoms:
        print("ERROR: no AOU geometries", file=sys.stderr)
        return 1

    # window bbox from timeseries
    bbox = ts.get("window_bbox") or [53.7, 17.9, 53.95, 18.15]
    catalog = open_catalog()
    units_by_id = {u["aou_id"]: u for u in (obs.get("units") or []) if u.get("aou_id")}
    added = 0

    for entry in dates:
        d = entry.get("date")
        if not d:
            continue
        product_id = entry.get("product_id") or ""
        tile = entry.get("tile")
        item = find_item(catalog, product_id, d, bbox, tile)
        if item is None:
            print(f"  skip {d}: no STAC item")
            continue
        print(f"  sampling date={d} item={item.id}")
        for aid, geom in aou_geoms.items():
            unit = units_by_id.setdefault(
                aid,
                {
                    "aou_id": aid,
                    "n_clear_dates": 0,
                    "observations": [],
                    "window_context_series": [],
                    "honesty": "AOU ledger append/upserts by (aou_id, date); STAC aou_direct backfill",
                },
            )
            existing_dates = {str(o.get("date")) for o in (unit.get("observations") or [])}
            if d in existing_dates:
                continue
            sample = sample_aou_on_item(item, geom)
            if not sample:
                print(f"    {aid}: insufficient clear pixels")
                continue
            month = int(d.split("-")[1])
            ag = agricultural_probability(
                ndvi=sample["ndvi"],
                ndmi=sample["ndmi"],
                ndre=None,
                ndre_available=False,
                n_clear_dates=1,  # provisional; unit n_clear updated after
                n_dates_above_bare=1 if sample["ndvi"] >= BARE_NDVI else 0,
                month=month,
            )
            row = {
                "aou_id": aid,
                "date": d,
                "ndvi": round(sample["ndvi"], 4),
                "ndmi": round(sample["ndmi"], 4),
                "ndre": None,
                "ndre_available": False,
                "agricultural_probability": ag.get("agricultural_probability"),
                "ag_class": ag.get("ag_class"),
                "alert": "healthy" if sample["ndvi"] >= BARE_NDVI else "bare",
                "clear_fraction": sample["clear_fraction"],
                "clear_fraction_basis": sample["clear_fraction_basis"],
                "pixel_count": sample["pixel_count"],
                "data_quality_confidence": 90.0,
                "source": sample["source"],
                "product_id": sample["product_id"],
                "tile": sample.get("tile") or tile,
                "cloud_cover": sample.get("cloud_cover"),
                "series_scope": "aou_direct",
                "refresh_status": "backfill_stac",
                "observation_role": "historical_observation",
                "assessability": "assessable",
                "valid_area_fraction": sample["clear_fraction"],
                "raw_measures": {
                    "ndvi": round(sample["ndvi"], 4),
                    "ndmi": round(sample["ndmi"], 4),
                },
                "derived_scores": {
                    "agricultural_probability": ag.get("agricultural_probability"),
                    "ag_class": ag.get("ag_class"),
                },
            }
            unit.setdefault("observations", []).append(row)
            added += 1
            print(f"    {aid}: ndvi={row['ndvi']} cf={row['clear_fraction']}")

    # Recompute n_clear + window context + sync registry lightly
    window_ctx = []
    for entry in dates:
        window_ctx.append(
            {
                "date": entry.get("date"),
                "ndvi": (entry.get("ndvi") or {}).get("mean"),
                "ndmi": (entry.get("ndmi") or {}).get("mean"),
                "series_scope": "window_not_aou",
                "note": "Window mean — AOI context only; not AOU ledger / n_clear",
            }
        )

    units_out = []
    for aid, unit in units_by_id.items():
        rows = [
            o
            for o in (unit.get("observations") or [])
            if o.get("series_scope") != "window_not_aou" and o.get("date") and o.get("ndvi") is not None
        ]
        rows.sort(key=lambda r: str(r["date"]))
        # drop accidental n_clear on rows
        for r in rows:
            r.pop("n_clear_dates", None)
        n_clear = len({str(r["date"]) for r in rows})
        unit["observations"] = rows
        unit["n_clear_dates"] = n_clear
        unit["window_context_series"] = window_ctx
        unit["honesty"] = (
            "AOU ledger append/upserts by (aou_id, date); "
            "window_context_series is context only (series_scope=window_not_aou); "
            "STAC aou_direct backfill for missing timeseries dates"
        )
        units_out.append(unit)
        # sync registry unit n_clear
        for ru in reg.get("units") or []:
            if ru.get("aou_id") == aid:
                ru["n_clear_dates"] = n_clear
                te = temporal_evidence_labels(n_clear)
                for k, v in te.items():
                    ru[k] = v
                pers_feat, n_seq, n_above = ledger_persistence_feature(rows, bare_ndvi=BARE_NDVI)
                ru["persistence_feature"] = pers_feat
                ru["n_dates_above_bare"] = n_above
                ru["persistence_status"] = persistence_status(n_clear)
                # demote class if still thin
                if n_clear < 2 and ru.get("ag_class") in ("likely", "very_likely"):
                    ru["ag_class"] = "possible"
                break

    obs_out = {
        "version": obs.get("version", "0.4.6-evaluator-deep-recheck"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "formula_ref": obs.get("formula_ref"),
        "units": units_out,
        "release_id": obs.get("release_id"),
        "run_id": obs.get("run_id"),
        "backfill": {
            "method": "stac_aou_direct",
            "added_rows": added,
            "note": "Prior timeseries dates sampled on AOU polygons; not window means",
        },
    }
    obs_path.write_text(json.dumps(obs_out, indent=2))
    reg_path.write_text(json.dumps(reg, indent=2))
    # mirror geojson props n_clear
    gj_path = out / "aou" / "aou_registry.geojson"
    if gj_path.exists():
        fc = json.loads(gj_path.read_text())
        by = {u["aou_id"]: u for u in units_out}
        for f in fc.get("features") or []:
            aid = (f.get("properties") or {}).get("aou_id")
            if aid in by:
                f["properties"]["n_clear_dates"] = by[aid]["n_clear_dates"]
                te = temporal_evidence_labels(by[aid]["n_clear_dates"])
                for k, v in te.items():
                    f["properties"][k] = v
        gj_path.write_text(json.dumps(fc))
    print(f"Backfill done: added_rows={added} units={len(units_out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
