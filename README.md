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

### Deprecated: `app/scripts/ingest_s2.py`

**Do not run** `app/scripts/ingest_s2.py` for production refresh. It is deprecated / unused reference code; its outputs are not read by the live UI.

Use the offline AOU pipeline instead:

    cd satellite/pipeline
    pip install -r requirements.txt
    MONITOR_OUT_DATA=../../app/public/data python run_monitor.py

Gallery STAC refresh (`stacRefresh.ts` browser path) is unchanged and independent of both scripts.

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

## v0.4 Phase-1 — Agricultural engines (this branch)

Binding science: `docs/SCIENCE_LOCKS_v0.4_phase1_2.md`  
Schemas: `docs/spec_0.4/`  
Roadmap (Phases 2–6 listed, not built): `docs/ROADMAP_v0.4_decision_engines.md`

### What Phase 1 ships

- Agricultural Probability Engine (expert v1 weights; NDRE renorm when unavailable)
- Persistent AOU IDs (`AOU-NJ-######`) via centroid + IoU ≥ 0.3 — never cell index
- Water / Vigor stress scores → existing alert codes
- Biotic risk flag `possible_biotic_stress` only (field verification; never pest certainty)
- NDRE when B05 (or documented B06/B07 fallback) present; else `ndre: null` + `ndre_available: false`
- Analysis UX: Overview / Spatial / Temporal / Decision (EN+AR)

### Out of scope here

Mountain decision UI; Suitability/Action ladder; Seed Intelligence; Field/Learning; fake live MPI/Khareef.

### Run

Full STAC monitor (writes alerts + calls AgProb engines):

```bash
cd satellite/pipeline
pip install -r requirements.txt
MONITOR_OUT_DATA=../../app/public/data python run_monitor.py
```

Offline enrich from existing `latest_alerts.geojson` (no PC raster re-read):

```bash
cd satellite/pipeline
MONITOR_OUT_DATA=../../app/public/data python run_ag_probability.py
```

Additional artifacts:

- `app/public/data/aou/aou_registry.geojson`
- `app/public/data/aou/aou_registry.json`
- `app/public/data/aou/aou_observations.json`

500 m grid remains fallback/debug (`geometry_kind=monitoring_grid_500m`); segmented AOUs are the product path.

