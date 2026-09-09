# Farm STAC monitor pipeline

## Output (Round 1)

Writes to `app/public/data/`:

- `latest_alerts.geojson` — includes `properties.source`, `date`, `last_updated`, alert counts
- `timeseries.json` — includes `source`, `generated_on`, `last_updated`, per-date product_id / tile / cloud_cover / citation
- `meta/last_refresh.json` — compact `{ last_updated, source, artifacts }` for Map/Imagery stamps

Override output directory with env `MONITOR_OUT_DATA`.

## Run locally

```bash
cd satellite/pipeline
pip install -r requirements.txt
MONITOR_OUT_DATA=../../app/public/data python run_monitor.py
```

## GitHub Action

See `GITHUB_ACTION_TEMPLATE.md` (copy later to `.github/workflows/monitor.yml`; workflows path not committed in Round-2 Path B).

## UI

Imagery page: client STAC **تحديث الصور** for latest clear scenes + honesty strip.
Full NDVI/NDMI GeoJSON refresh is this pipeline / Action — not implied by mountain MPI.


## v0.4 Phase-1 engines

After `run_monitor.py` (or standalone):

```bash
MONITOR_OUT_DATA=../../app/public/data python run_ag_probability.py
```

Formulas locked by `docs/SCIENCE_LOCKS_v0.4_phase1_2.md` (not `spec_pending`).
NDRE: `(B08-B05)/(B08+B05)`; B06/B07 documented fallback only; else renorm AgProb.
AOU identity: `AOU-NJ-######`, centroid + IoU≥0.3, min ~2 ha.

## SWIR feature (AgProb)

Offline enrichment may use `feature_swir_response` (NDVI+NDMI proxy) — that is OK when B11/B12 are unavailable. When the STAC path has B11/B12, prefer passing `swir_feature` derived from SWIR brightness into `agricultural_probability` (hook already exists on the engine); keep the NDVI+NDMI proxy only as fallback.
