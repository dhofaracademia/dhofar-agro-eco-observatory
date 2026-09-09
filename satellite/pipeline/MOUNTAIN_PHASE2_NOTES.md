# Mountain Phase-2 notes — MPI offline evidence (v0.4)

**Status:** `pilot_unverified` / `provisional` — offline artifacts only.  
**UI gate:** **No** partner Map / Analysis / Restoration mountain decision UI.  
**Never write** to `app/public/` until science re-sign-off.

**Binding:** `docs/SCIENCE_LOCKS_v0.4_phase1_2.md` §5 MPI + §6 regeneration ladder + Forbidden table.

## Scripts

| Script | Role |
|--------|------|
| `run_mountain_pilot.py` | DEM elev/slope/aspect/TWI + pre/post NDMI; stratified sample |
| `run_mountain_mpi.py` | MPI curve T0…T+6w, classes, regen stubs; calls shared DEM helpers |
| `engines/mpi.py` | Classify + stratified sample + ladder enum stubs |

## Artifact paths (Agrofostery / CoS review)

```
satellite/pipeline/artifacts/mountain_pilot/
  pilot_terrain.geojson          # full grid (gitignored)
  pilot_terrain.sample.geojson   # stratified elev×slope (committed)
  pilot_terrain.schema.json
  run_meta.json
  mpi/
    mpi_curve.json               # AOI-level curve + class
    mpi_cells.geojson            # stratified cells (gitignored if large)
    mpi_cells.sample.geojson     # compact review sample
    mpi_run_meta.json            # T0 method, windows, clear counts
    regeneration_ladder.stubs.json
```

Schemas: `docs/spec_0.4/moisture_persistence.schema.json`, `natural_regeneration_ladder.schema.json`.

## Locked bbox (WGS84 W,S,E,N)

`[54.05, 17.08, 54.22, 17.22]` — Jabal Qara fog-escarpment. Unchanged unless DEM demands ≤0.05° nudge (note required).

## T0 method (dynamic, documented)

1. **Preferred:** first clear Sentinel-2 L2A scene in **post-khareef / late Sep–Oct** window (default `2026-09-15/2026-10-31`).
2. **Fallback:** first clear scene in **onset** window (default `2026-06-01/2026-06-21`) if post window has zero usable STAC candidates.
3. **Not** a live Khareef “detected onset” product (Forbidden without EO/climate method + QA).

Samples at **T0, T+1w, T+2w, T+4w, T+6w** with multi-scene search **±3 days**. Gaps → `ndmi=null` / status `gap`. **No interpolation / fabricated NDMI.**

## Classes (§5.2)

| Class | Rule |
|-------|------|
| High | ≥3 valid; above dry baseline through T+4 or slow decay |
| Medium | 2–3+ valid; mixed / moderate decay |
| Low | Rapid return by T+2, or only T0 wet |
| Insufficient | <2 valid → **no class** (fail-honest) |

Stamp: `status: pilot_unverified`, `layer: mountain_mpi_phase2`, `provisional: true`.  
**NDMI / MPI ≠ soil moisture %.**

## DEM / TWI

- **DEM:** Copernicus GLO-30 via Planetary Computer (`nasadem` fallback in shared helper).
- **TWI:** Topographic Wetness **Proxy** only (coarse uphill-neighbor) — not full hydrology.

## Regeneration ladder (§6)

Enum + rule stubs only (`regeneration_ladder.stubs.json`).  
**Forbidden:** numeric suitability→action auto-assign; campaign ha / seed kg / crew days as official; partner-facing ladder fields on decision UI.

## How to run

```bash
cd satellite/pipeline
pip install -r requirements.txt
python run_mountain_mpi.py --dry-run
python run_mountain_mpi.py
# defaults: --post-range 2026-09-15/2026-10-31 --onset-range 2026-06-01/2026-06-21
```

## Spot-check paths for science

1. `artifacts/mountain_pilot/mpi/mpi_run_meta.json` — T0 method, windows, per-lag clear_frac / product / tile / cloud %.
2. `artifacts/mountain_pilot/mpi/mpi_curve.json` — AOI curve points (nulls on gaps).
3. `artifacts/mountain_pilot/mpi/mpi_cells.sample.geojson` — stratified cells with `mpi_class_display`.
4. `artifacts/mountain_pilot/pilot_terrain.sample.geojson` — elev×slope strata tags.
5. Confirm no `app/public/` mountain MPI wire; no suitability/action/species on features.

## Gaps / honesty

1. Late Sep–Oct **2026** may be empty in STAC until scenes are acquired/ingested after early September — runner fails honest or falls back to documented onset T0.
2. Peak Khareef weeks after an onset T0 are often cloudy → many `gap` points → Insufficient class expected.
3. Prior Sep 1–8 2026 post window failed SCL clear_frac=0.0 — do not invent values.
4. No partner UI; no Phase-3 Suitability productization in this PR.

## First Phase-2 E2E (2026-09-09 UTC / Asia/Muscat)

| Item | Result |
|------|--------|
| DEM | Copernicus GLO-30; elev slope p90 ≈ 26.9°; bbox **unchanged** |
| Post window `2026-09-15/2026-10-31` | **0 STAC candidates** (catalog empty after ~2026-09-06) — fail-honest |
| T0 | **2026-06-01** onset fallback; tile `39QZV`; cloud ≈ 0.0004%; documented in `mpi_run_meta.json` |
| T0 / T+1w / T+2w NDMI | OK (clear_frac ≈ 1.0) |
| T+4w / T+6w | **gap** (null NDMI — not fabricated) |
| AOI `mpi_class` | Low (all valid NDMI ≤ dry baseline; provisional) with n_valid=3 |
| Terrain sample | Stratified 8×6 strata (low/mid/high × gentle/steep) |
| UI / app/public | Not written |

Re-run after late Sep–Oct 2026 scenes ingest to prefer post-khareef T0.
