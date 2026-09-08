# مرصد ظفار الزراعي البيئي | Dhofar Agro & Eco Observatory

Bilingual decision-support observatory for Dhofar, Oman.

- Agricultural Observatory — AOU monitoring
- Restoration Observatory — Khareef / mountain intelligence

Imagery Refresh uses Microsoft Planetary Computer STAC (Sentinel-2 L2A). Contains modified Copernicus Sentinel data (ESA). Optional env: `VITE_STAC_SEARCH_URL` (no secrets in repo).

App lives in `app/`.

## Partner FAQ

### What does Gallery Refresh scene list from STAC do?

It queries Microsoft Planetary Computer STAC for recent Sentinel-2 L2A items over the farm corridor and updates the Imagery scene list in the browser (cached in localStorage).

It does **not**:

- recompute AOU alerts / latest_alerts.geojson
- refresh timeseries.json or mountain MPI / suitability stubs
- invent live Khareef onset or official farm boundaries

### How do I refresh the AOU / farm-monitor layer?

Run the offline pipeline (same outputs the UI reads from app/public/data/):

Commands:

    cd satellite/pipeline
    pip install -r requirements.txt
    MONITOR_OUT_DATA=../../app/public/data python run_monitor.py

Writes:

- app/public/data/latest_alerts.geojson
- app/public/data/timeseries.json
- app/public/data/meta/last_refresh.json

### Scheduled monitor Action

Template: satellite/pipeline/GITHUB_ACTION_TEMPLATE.md

If monitor.yml is installed under the repo Actions workflows folder on the default branch, use Actions then Farm STAC / AOU monitor (manual run + weekly cron).

Enable steps when missing or restricted:

1. Copy YAML from the template into the Actions workflows folder as monitor.yml
2. Allow Actions plus contents write for the job
3. Run a manual dispatch once and confirm app/public/data artifacts update

Until enabled on main, do **not** assume the scheduled monitor is live — use run_monitor.py locally.

### Honesty locks (unchanged)

- Fog-only T. dhofarica; Suitability != Confidence; no hydrology claims; four farm codes; no fake live MPI/Khareef; AOU != official farm; STAC refresh != AOU recompute.
