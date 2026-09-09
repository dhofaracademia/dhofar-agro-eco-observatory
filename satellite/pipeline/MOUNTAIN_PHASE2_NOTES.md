# Mountain Phase-2 notes — onset-window dry MPI evidence (v0.4)

**This run is onset-window dry MPI evidence** (`t0_source_window: onset`, `evidence_window: onset`, `product_kind: onset_window_dry_mpi_provisional`).  
It is **NOT** post-khareef moisture persistence / recovery. Do **not** read AOI `mpi_class: Low` as “failed post-khareef recovery.” Low here means NDMI stayed at/below dry baseline under an **onset** T0 — not a failed post-khareef persistence assessment. True `post_khareef_mpi` requires late Sep–Oct clear scenes (preferred T0 window).

**Status:** `pilot_unverified` / `provisional` — offline artifacts only.  
**UI gate:** **No** partner Map / Analysis / Restoration mountain decision UI.  
**Never write** to `app/public/` until science re-sign-off.

**Binding:** `docs/SCIENCE_LOCKS_v0.4_phase1_2.md` §5 MPI + §6 regeneration ladder + Forbidden table.

## Scripts

| Script | Role |
|--------|------|
| `run_mountain_pilot.py` | DEM elev/slope/aspect/TWI + pre/post NDMI; stratified sample |
| `run_mountain_mpi.py` | MPI curve T0…T+6w, classes, regen stubs; calls shared DEM helpers |
| `engines/mpi.py` | Classify + stratified sample (+ fog-belt elev>600 ensure) + ladder enum stubs |

## Artifact paths (Agrofostery / CoS review)

```
satellite/pipeline/artifacts/mountain_pilot/
  pilot_terrain.geojson          # full grid (gitignored)
  pilot_terrain.sample.geojson   # stratified elev×slope + fog-belt >600 m (committed)
  pilot_terrain.schema.json
  run_meta.json
  mpi/
    mpi_curve.json               # AOI-level curve + class (onset labeling front-loaded)
    mpi_cells.geojson            # stratified cells (gitignored if large)
    mpi_cells.sample.geojson     # compact review sample (includes elev>600 when present)
    mpi_run_meta.json            # T0 method, windows, clear counts + onset product_kind
    regeneration_ladder.stubs.json
```

Schemas: `docs/spec_0.4/moisture_persistence.schema.json`, `natural_regeneration_ladder.schema.json`.

## Locked bbox (WGS84 W,S,E,N)

`[54.05, 17.08, 54.22, 17.22]` — Jabal Qara fog-escarpment. Unchanged unless DEM demands ≤0.05° nudge (note required).

## T0 method (dynamic, documented)

1. **Preferred:** first clear Sentinel-2 L2A scene in **post-khareef / late Sep–Oct** window (default `2026-09-15/2026-10-31`) → then product may be labeled `post_khareef_mpi`.
2. **Fallback (this E2E):** first clear scene in **onset** window (default `2026-06-01/2026-06-21`) if post window has zero usable STAC candidates → stamp `evidence_window: onset` / `product_kind: onset_window_dry_mpi_provisional`.
3. **Not** a live Khareef “detected onset” product (Forbidden without EO/climate method + QA).

Samples at **T0, T+1w, T+2w, T+4w, T+6w** with multi-scene search **±3 days**. Gaps → `ndmi=null` / status `gap`. **No interpolation / fabricated NDMI.**

## Classes (§5.2)

Class **values** unchanged: High / Medium / Low / Insufficient.

| Class | Rule |
|-------|------|
| High | ≥3 valid; above dry baseline through T+4 or slow decay |
| Medium | 2–3+ valid; mixed / moderate decay |
| Low | Rapid return by T+2, or only T0 wet / all ≤ dry baseline |
| Insufficient | <2 valid → **no class** (fail-honest) |

**Onset-window disclaimer (EN):** Low here means NDMI stayed at/below dry baseline under an **onset** T0 — not a failed post-khareef persistence assessment.  
**Onset-window disclaimer (AR):** تصنيف Low هنا يعني أن NDMI بقي عند أو دون خط الأساس الجاف تحت نافذة بداية الموسم (onset) لـ T0 — وليس تقييم فشل استمرارية الرطوبة بعد موسم الخريف.

Stamp: `status: pilot_unverified`, `layer: mountain_mpi_phase2`, `provisional: true`, `interpretation: provisional_dry_onset_evidence`.  
**NDMI / MPI ≠ soil moisture %.**

## DEM / TWI / stratified sample

- **DEM:** Copernicus GLO-30 via Planetary Computer (`nasadem` fallback in shared helper). DEM in locked bbox reaches ~816 m; fog-belt absolute band elev>600 m is present (n≈143 in full grid).
- **TWI:** Topographic Wetness **Proxy** only (coarse uphill-neighbor) — not full hydrology.
- **Sample:** elev tertile × slope median, **plus** forced inclusion of fog-belt elev>600 m when present (`engines/mpi.py` → `stratified_sample_indices(..., ensure_elev_gt=600)`). Committed `pilot_terrain.sample.geojson` / `mpi_cells.sample.geojson` refreshed from local full grids (gitignored) — no invented elevations. If a future bbox has none >600 m, stamp `fog_belt_universe_n: 0` in meta and keep quantile strata only.

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

1. `artifacts/mountain_pilot/mpi/mpi_run_meta.json` — front-loaded `evidence_window` / `product_kind` / `t0_source_window: onset`; T0 method; fog_belt_sample.
2. `artifacts/mountain_pilot/mpi/mpi_curve.json` — same onset labeling + `mpi_class` + disclaimers.
3. `artifacts/mountain_pilot/mpi/mpi_cells.sample.geojson` — stratified cells incl. elev>600 when present.
4. `artifacts/mountain_pilot/pilot_terrain.sample.geojson` — elev×slope strata + fog-belt ensure.
5. Confirm no `app/public/` mountain MPI wire; no suitability/action/species on features.

## Gaps / honesty

1. Late Sep–Oct **2026** may be empty in STAC until scenes are acquired/ingested after early September — runner fails honest or falls back to documented onset T0.
2. Peak Khareef weeks after an onset T0 are often cloudy → many `gap` points → Insufficient class expected; dry onset curves often yield **Low** — that is **not** post-khareef recovery failure.
3. Prior Sep 1–8 2026 post window failed SCL clear_frac=0.0 — do not invent values.
4. No partner UI; no Phase-3 Suitability productization in this PR.

## First Phase-2 E2E (2026-09-09 UTC / Asia/Muscat)

| Item | Result |
|------|--------|
| DEM | Copernicus GLO-30; elev slope p90 ≈ 26.9°; elev max ≈ 816 m; bbox **unchanged** |
| Post window `2026-09-15/2026-10-31` | **0 STAC candidates** (catalog empty after ~2026-09-06) — fail-honest |
| T0 | **2026-06-01** onset fallback; tile `39QZV`; cloud ≈ 0.0004%; `t0_source_window: onset` |
| Product label | `product_kind: onset_window_dry_mpi_provisional` — **not** `post_khareef_mpi` |
| T0 / T+1w / T+2w NDMI | OK (clear_frac ≈ 1.0) |
| T+4w / T+6w | **gap** (null NDMI — not fabricated) |
| AOI `mpi_class` | Low (all valid NDMI ≤ dry baseline; provisional) with n_valid=3 — **onset dry evidence**, not post-khareef failure |
| Terrain / MPI sample | Stratified 8×6 + forced fog-belt elev>600 m (4 cells in each committed sample) |
| UI / app/public | Not written |

Re-run after late Sep–Oct 2026 scenes ingest to prefer post-khareef T0; only then may product_kind move off onset provisional.
