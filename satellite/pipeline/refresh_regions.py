"""Independent regional vegetation observations; never extends agricultural AOU claims.

Fixed equal-area grid, polygon masking, same-day tile mosaics, no duplicate pixels.
60 m nearest-neighbour samples are explicitly estimates, not exhaustive native pixels.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import planetary_computer as pc
import rasterio
from affine import Affine
from pyproj import CRS, Transformer
from pystac_client import Client
from pystac_client.stac_api_io import StacApiIO
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.vrt import WarpedVRT
from shapely.geometry import shape, mapping, box
from shapely.ops import transform as transform_geometry

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('REGIONS_OUT_DATA', str(ROOT / 'app/public/data/regions')))
BOUNDARIES = ROOT / 'app/public/data/regions/boundaries.geojson'
CRS_AREA = CRS.from_proj4('+proj=laea +lat_0=18 +lon_0=54 +datum=WGS84 +units=m +no_defs')
FORWARD = Transformer.from_crs(4326, CRS_AREA, always_xy=True).transform
INVERSE = Transformer.from_crs(CRS_AREA, 4326, always_xy=True).transform
RESOLUTION = 60
BLOCK = 16  # 960 m display cells, clipped to the study polygon
MIN_SAMPLES = 50
MIN_FRACTION = 0.5


def load_regions():
    regions = json.loads(BOUNDARIES.read_text())['features']
    ids = set()
    for region in regions:
        geom = shape(region['geometry'])
        ident = region['properties']['id']
        if ident in ids or not geom.is_valid or geom.is_empty or geom.geom_type != 'Polygon':
            raise ValueError('Invalid/duplicate region geometry')
        ids.add(ident)
        w, s, e, n = geom.bounds
        if not (52 <= w < e <= 56 and 16 <= s < n <= 20):
            raise ValueError('Region outside expected Dhofar coordinate range')
    for i, a in enumerate(regions):
        for b in regions[i+1:]:
            if shape(a['geometry']).intersection(shape(b['geometry'])).area > 1e-10:
                raise ValueError('Study regions overlap')
    return regions


def grid_for(geometry):
    polygon = transform_geometry(FORWARD, shape(geometry).segmentize(0.005))
    left, bottom, right, top = polygon.bounds
    left, bottom = math.floor(left/960)*960, math.floor(bottom/960)*960
    right, top = math.ceil(right/960)*960, math.ceil(top/960)*960
    width, height = int((right-left)/RESOLUTION), int((top-bottom)/RESOLUTION)
    affine = Affine(RESOLUTION, 0, left, 0, -RESOLUTION, top)
    inside = geometry_mask([mapping(polygon)], (height, width), affine, invert=True)
    if not inside.any():
        raise ValueError('Empty sampling grid')
    return polygon, affine, inside


def read_band(item, key, affine, dimensions):
    asset = item.assets[key]
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT=60,
                      GDAL_HTTP_CONNECTTIMEOUT=15, GDAL_HTTP_MAX_RETRY=2):
        with rasterio.open(pc.sign(asset.href)) as src:
            if src.crs is None:
                raise ValueError('Raster CRS missing')
            with WarpedVRT(src, crs=CRS_AREA, transform=affine,
                           height=dimensions[0], width=dimensions[1],
                           resampling=Resampling.nearest, nodata=0) as vrt:
                data = vrt.read(1).astype('float32')
    if key == 'SCL':
        return data
    missing = data == 0
    metadata = asset.extra_fields.get('raster:bands', [{}])[0]
    scale = metadata.get('scale', 0.0001)
    if 'offset' in metadata:
        offset = metadata['offset']
    else:
        baseline = item.properties.get('s2:processing_baseline')
        if baseline is None:
            raise ValueError('Unknown radiometric baseline')
        offset = -0.1 if float(baseline) >= 4 else 0.0
    data = data * scale + offset
    data[missing] = np.nan
    return data


def mosaic_day(items, affine, inside):
    ndvi = np.full(inside.shape, np.nan, dtype='float32')
    ndmi = np.full(inside.shape, np.nan, dtype='float32')
    sources = []
    for item in sorted(items, key=lambda it: (it.properties.get('eo:cloud_cover', 100), it.id)):
        if not all(k in item.assets for k in ('B04', 'B08', 'B11', 'SCL')):
            raise ValueError('Required spectral/cloud mask asset missing')
        red, nir, swir, scl = [read_band(item, k, affine, inside.shape) for k in ('B04','B08','B11','SCL')]
        valid = (inside & np.isnan(ndvi) & np.isin(scl, [4, 5])
                 & np.isfinite(red) & np.isfinite(nir) & np.isfinite(swir)
                 & (red >= 0) & (nir > 0) & (swir >= 0)
                 & (red <= 1) & (nir <= 1) & (swir <= 1))
        ndvi[valid] = (nir[valid]-red[valid])/(nir[valid]+red[valid])
        ndmi[valid] = (nir[valid]-swir[valid])/(nir[valid]+swir[valid])
        sources.append({'id': item.id, 'datetime': item.datetime.isoformat()})
    return ndvi, ndmi, sources


def summarize(region, latest, previous=None):
    polygon, affine, inside = grid_for(region['geometry'])
    ndvi, ndmi = latest['ndvi'], latest['ndmi']
    if ndvi.shape != inside.shape or ndmi.shape != inside.shape:
        raise ValueError('Raster/grid shape mismatch')
    clear = inside & np.isfinite(ndvi) & np.isfinite(ndmi)
    total, valid = int(inside.sum()), int(clear.sum())
    features = []
    for row in range(0, inside.shape[0], BLOCK):
        for col in range(0, inside.shape[1], BLOCK):
            sl = np.s_[row:row+BLOCK, col:col+BLOCK]
            n = int(inside[sl].sum())
            x, y = affine * (col, row)
            cell = box(x, y-BLOCK*RESOLUTION, x+BLOCK*RESOLUTION, y).intersection(polygon)
            if cell.is_empty or cell.area == 0:
                continue
            good = clear[sl]
            count = int(good.sum())
            assessable = n > 0 and count >= MIN_SAMPLES and count/n >= MIN_FRACTION
            delta = None
            if assessable and previous is not None:
                # Compare the SAME sample locations, never different cloud-free subsets.
                common = good & np.isfinite(previous['ndvi'][sl]) & np.isfinite(previous['ndmi'][sl])
                if int(common.sum()) >= MIN_SAMPLES and common.sum()/n >= MIN_FRACTION:
                    delta = round(float(np.mean(ndvi[sl][common]-previous['ndvi'][sl][common])), 4)
            features.append({'type':'Feature', 'geometry':mapping(transform_geometry(INVERSE, cell.segmentize(240))), 'properties':{
                'id':f"{region['properties']['id']}:{row}:{col}", 'region_id':region['properties']['id'],
                'clear_fraction':round(count/n, 4) if n else 0, 'valid_samples':count, 'total_samples':n,
                'ndvi':round(float(ndvi[sl][good].mean()),4) if assessable else None,
                'ndmi':round(float(ndmi[sl][good].mean()),4) if assessable else None,
                'ndvi_change':delta, 'date':latest['date'],
                'previous_date':previous['date'] if previous else None,
                'status':'observed' if assessable else 'insufficient_observations'}})
    return {'region_id':region['properties']['id'], 'date':latest['date'],
            'previous_date':previous['date'] if previous else None,
            'area_km2':round(polygon.area/1e6,2),
            'estimated_clear_area_km2':round(polygon.area/1e6*valid/total,2),
            'clear_fraction':round(valid/total,4), 'valid_samples':valid, 'total_samples':total,
            'sources':latest['sources'], 'previous_sources':previous['sources'] if previous else [],
            'cells':features}


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',',':'))+'\n')
    tmp.replace(path)


def main():
    regions = load_regions()
    now = datetime.now(timezone.utc)
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        version = hashlib.sha256(BOUNDARIES.read_bytes()).hexdigest()
        existing_path = OUT/'observations.json'
        existing = json.loads(existing_path.read_text()) if existing_path.exists() else {}
        cached = {r['region_id']:r for r in existing.get('regions', [])} if existing.get('boundary_sha256') == version and existing.get('method_version') == 2 else {}
        catalog = Client.open('https://planetarycomputer.microsoft.com/api/stac/v1',
                              stac_io=StacApiIO(timeout=30, max_retries=2))
        results = []
        for region in regions:
            items = list(catalog.search(collections=['sentinel-2-l2a'], intersects=region['geometry'],
                datetime=f'{(now-timedelta(days=60)).date()}/{now.date()}',
                query={'eo:cloud_cover':{'lt':80}}, max_items=200,
                sortby=[{'field':'datetime','direction':'desc'}]).items())
            by_date = defaultdict(list)
            for item in items:
                by_date[item.datetime.date().isoformat()].append(item)
            if not by_date:
                raise ValueError(f"No scenes for {region['properties']['id']}")
            dates = sorted(by_date, reverse=True)
            chosen = [dates[0]]
            # Earlier comparison must be at least five days apart.
            older = [d for d in dates[1:] if (datetime.fromisoformat(dates[0])-datetime.fromisoformat(d)).days >= 5]
            if older:
                chosen.append(older[0])
            old = cached.get(region['properties']['id'])
            current_ids = {it.id for it in by_date[chosen[0]]}
            previous_ids = {it.id for it in by_date[chosen[1]]} if len(chosen)>1 else set()
            if old and current_ids == {s['id'] for s in old['sources']} and previous_ids == {s['id'] for s in old['previous_sources']}:
                results.append(old)
                print(region['properties']['id'], 'unchanged scenes', flush=True)
                continue
            _, affine, inside = grid_for(region['geometry'])
            observations = []
            for day in chosen:
                v, m, sources = mosaic_day(by_date[day], affine, inside)
                observations.append(dict(date=day, ndvi=v, ndmi=m, sources=sources))
            results.append(summarize(region, observations[0], observations[1] if len(observations)>1 else None))
            print(region['properties']['id'], results[-1]['date'], results[-1]['clear_fraction'], flush=True)
        version = hashlib.sha256(BOUNDARIES.read_bytes()).hexdigest()
        # A single document atomically holds summaries and cells; no cross-file release mismatch.
        atomic_json(OUT/'observations.json', {'schema_version':1, 'method_version':2, 'boundary_sha256':version,
            'generated_at':now.isoformat(), 'sample_spacing_m':RESOLUTION, 'cell_size_m':960,
            'method':'Processing-baseline reflectance offsets applied. Nearest-neighbour 60 m samples; SCL classes 4/5 only; estimated clear land area; not crop classification or soil moisture.',
            'regions':results})
        atomic_json(OUT/'status.json', {'status':'success','checked_at':now.isoformat()})
    except Exception as exc:
        # The previous complete observation document stays untouched.
        atomic_json(OUT/'status.json', {'status':'failed','checked_at':now.isoformat(),'error':type(exc).__name__})
        raise

if __name__ == '__main__':
    main()
