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
