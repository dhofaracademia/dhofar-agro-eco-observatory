# Farm STAC monitor pipeline

## Output (Round 1)

Writes to `app/public/data/`:

- `latest_alerts.geojson` — includes `properties.source`, `date`, `last_updated`, alert counts
- `timeseries.json` — includes `source`, `generated_on`, `last_updated`, per-date product_id / tile / cloud_cover / citation

Override output directory with env `MONITOR_OUT_DATA`.

## Run locally

```bash
cd satellite/pipeline
pip install planetary-computer pystac-client rasterio shapely numpy pyproj
MONITOR_OUT_DATA=../../app/public/data python run_monitor.py
```

## GitHub Action

`.github/workflows/refresh-farm-stac.yml` — workflow_dispatch + weekly Monday 06:00 UTC.

## UI

Imagery page: client STAC **تحديث الصور** for latest clear scenes + honesty strip.
Full NDVI/NDMI GeoJSON refresh is this pipeline / Action — not implied by mountain MPI.
