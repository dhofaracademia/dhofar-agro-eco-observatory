# Najd satellite monitor — run notes (2026-09-08)

## What ran

Reproducible pipeline: `/workspace/najd-satellite/pipeline/run_monitor.py`

```bash
# Requires packages in /workspace/mapvenv (rasterio, pystac-client, planetary-computer, numpy, shapely, pyproj)
PYTHONPATH=/workspace/mapvenv/lib/python3.13/site-packages \
  /usr/bin/python3 /workspace/najd-satellite/pipeline/run_monitor.py
# or: /workspace/mapvenv/bin/python /workspace/najd-satellite/pipeline/run_monitor.py
```

Runtime (~40 s): STAC search + windowed HTTP COG reads of B04/B08/B11/SCL (no full-tile download).

## Sources

- **Collection:** Copernicus Sentinel-2 L2A (ESA)
- **Access:** Microsoft Planetary Computer STAC  
  `https://planetarycomputer.microsoft.com/api/stac/v1` collection `sentinel-2-l2a`
- **Citation string on every feature/record:**  
  `Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer`

## AOI / window

| | bbox [W, S, E, N] |
|--|--|
| Full AOI | `[53.4, 17.5, 54.3, 18.5]` |
| Analysis window (farm corridor) | `[53.7, 17.9, 53.95, 18.15]` (~0.25° × 0.25°, center ~53.825E 18.025N) |

Priority MGRS tiles: `39QZV`, `39QYA`, `39QZA`, `39QYV`.  
Filter: `eo:cloud_cover < 10`.

## Scenes used (real 2026 acquisitions)

| Date | Product ID | Tile | Cloud % | Valid pixels |
|------|------------|------|---------|--------------|
| 2026-08-17 | `S2A_MSIL2A_20260817T070431_R020_T39QYA_20260817T093558` | 39QYA | 9.68 | 4,522,421 |
| 2026-08-25 | `S2C_MSIL2A_20260825T064621_R020_T39QYA_20260825T115811` | 39QYA | 0.00 | 4,522,421 |
| 2026-08-30 | `S2B_MSIL2A_20260830T064619_R020_T39QZA_20260830T103855` | 39QZA | 0.00 | 2,323,253 (partial tile overlap) |
| 2026-09-06 | `S2A_MSIL2A_20260906T070431_R020_T39QYA_20260906T093909` | 39QYA | 0.87 | 4,522,421 |

Span ≈ 20 days (weekly-ish change across 4 dates).

## Index method (proved with sample stats)

- Reflectance scale: DN / 10000  
- **NDVI** = (B08 − B04) / (B08 + B04)  
- **NDMI** = (B08 − B11) / (B08 + B11)  
- SCL used when available to drop cloud / nodata classes (0,1,8,9,10)  
- Aggregation: ~500 m grid cells; mean NDVI/NDMI + pixel count

### Sample pixel-level stats (window, latest 2026-09-06, tile 39QYA)

| Index | mean | p10 | p50 | p90 |
|-------|------|-----|-----|-----|
| NDVI | 0.0712 | 0.0388 | 0.0532 | 0.0657 |
| NDMI | −0.1011 | −0.1230 | −0.1104 | −0.0856 |

Desert background dominates (low NDVI, negative NDMI). Vegetated farm cells appear in the upper tail (example healthy cell NDVI ≈ 0.64, NDMI ≈ 0.22).

### 2026-08-17 sample

| Index | mean | p50 |
|-------|------|-----|
| NDVI | 0.0688 | 0.0546 |
| NDMI | −0.1045 | −0.1126 |

## Alerts (latest date 2026-09-06 → `latest_alerts.geojson`)

Relative rules among vegetated cells (NDVI ≥ 0.18):

- **water_attention:** NDMI below 25th percentile of vegetated peers  
- **vigor_attention:** NDVI below 25th percentile of vegetated peers (management flag — **not** a fertilizer diagnosis)  
- **healthy / bare / unclear** as appropriate  

| alert | count |
|-------|------:|
| bare | 1770 |
| healthy | 65 |
| water_attention | 26 |
| vigor_attention | 11 |
| **TOTAL** | **1872** |

## Outputs (absolute paths)

- `/workspace/najd-satellite/pipeline/run_monitor.py` — reproducible script  
- `/workspace/najd-planting-monitor/public/data/latest_alerts.geojson` — 1872 Polygon features  
- `/workspace/najd-planting-monitor/public/data/timeseries.json` — 4-date summary + citations  
- `/workspace/najd-satellite/pipeline/RUN_NOTES.md` — this file  

## Caveats

1. **Relative alerts only** — not agronomic diagnosis; no soil/irrigation ground truth applied.  
2. **Bare desert majority** — expected for Najd; farm signals are sparse bright NDVI patches.  
3. **2026-08-30** uses tile `39QZA` (best available that day); window only partially covered → fewer valid pixels. Prefer same tile across dates for strict change detection (re-run can bias tile preference).  
4. **Windowed COG reads** depend on Planetary Computer SAS signing; tokens expire — re-run script to refresh.  
5. Grid is coarse (~500 m); sub-field variability is averaged.  
6. No inventory of farm parcels yet — alerts are geographic cells, not named farms.

## Errors

None on this run (`errors: []` in timeseries.json).
