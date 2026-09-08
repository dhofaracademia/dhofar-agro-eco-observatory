# GitHub Action template — farm STAC / AOU monitor

> **Not committed under `.github/workflows/` in this PR.**  
> GitHub Contents API historically blocks writes to workflow paths for this repo.  
> Copy the YAML below to `.github/workflows/monitor.yml` (or `refresh-farm-stac.yml`) via a maintainer with workflow write access when you are ready to enable scheduled runs.

## What it does

- `workflow_dispatch` (manual) + weekly `cron`
- Installs `satellite/pipeline/requirements.txt`
- Runs `run_monitor.py` with `MONITOR_OUT_DATA=app/public/data`
- Commits refreshed `latest_alerts.geojson`, `timeseries.json`, and `meta/last_refresh.json` back to the default branch (optional — disable the commit step if you prefer artifact-only)

## Copy to `.github/workflows/monitor.yml`

```yaml
name: Farm STAC / AOU monitor

on:
  workflow_dispatch:
  schedule:
    # Mondays 06:00 UTC
    - cron: "0 6 * * 1"

permissions:
  contents: write

jobs:
  monitor:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: satellite/pipeline
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: satellite/pipeline/requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run monitor
        env:
          MONITOR_OUT_DATA: ${{ github.workspace }}/app/public/data
        run: python run_monitor.py

      - name: Commit refreshed farm data (optional)
        working-directory: ${{ github.workspace }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add app/public/data/latest_alerts.geojson \
                  app/public/data/timeseries.json \
                  app/public/data/meta/last_refresh.json
          if git diff --staged --quiet; then
            echo "No farm-data changes"
          else
            git commit -m "data: refresh farm STAC / AOU offline run"
            git push
          fi
```

## Local run (same outputs)

```bash
cd satellite/pipeline
pip install -r requirements.txt
MONITOR_OUT_DATA=../../app/public/data python run_monitor.py
```

Writes:

- `app/public/data/latest_alerts.geojson`
- `app/public/data/timeseries.json`
- `app/public/data/meta/last_refresh.json` — `{ "last_updated", "source": "run_monitor", "artifacts": [...] }`

## Honesty note for UI

Gallery **Refresh scene list from STAC** only updates the client-side STAC scene listing.  
It does **not** recompute AOU alerts or MPI. Those come from this offline / Action pipeline.
