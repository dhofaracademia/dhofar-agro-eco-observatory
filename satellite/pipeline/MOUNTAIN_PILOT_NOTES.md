# Mountain pilot notes (Round-4 Track 2) — science review

**Status:** `pilot_unverified` — raw DEM+TWI+NDMI grid only. **Not** wired into Map / Gallery / Restoration UI.

**Script:** `satellite/pipeline/run_mountain_pilot.py`  
**Phase-2 MPI:** `run_mountain_mpi.py` → see `MOUNTAIN_PHASE2_NOTES.md`  
**Artifacts (UI-safe):** `satellite/pipeline/artifacts/mountain_pilot/`  
Full `pilot_terrain.geojson` is gitignored (can be large). Commit keeps `pilot_terrain.sample.geojson`, `pilot_terrain.schema.json`, `run_meta.json`.

## Locked bbox (WGS84 W,S,E,N)

```
[54.05, 17.08, 54.22, 17.22]
```

- **Site:** Jabal Qara fog-escarpment (CoS / AgriTech science lock, 2026-09-08).
- **Span:** ~0.17° lon × ~0.14° lat (within ≤~0.2° per side).
- **Rule:** No change before first DEM visual check. After check, nudge ≤0.05° only, with a note here.
- **Superseded guesses:** 17.05–17.25N / 54.05–54.25E and AgriTech draft `[54.02, 17.02, 54.08, 17.08]` — do not revert without CoS.

## DEM source (first E2E, 2026-09-08)

- **Used:** Copernicus DEM GLO-30 (`cop-dem-glo-30`) via Microsoft Planetary Computer.
- **Fallback (code path):** NASADEM / SRTM (`nasadem`) if GLO-30 unavailable.
- **Window stats (first run):** elev ≈ 27–828 m (mean ~306 m); slope p90 ≈ 26.9° — **not flat**; consistent with escarpment, so **bbox not nudged**.
- Per cell: `elevation_m`, `slope_deg`, `aspect_deg`, `twi`.

## NDMI / SCL (fail-honest) — first E2E

| Window | Range | Result |
|--------|-------|--------|
| Pre-khareef | 2026-05-01/2026-05-31 | OK — tile `40QBE`, cloud≈0.01%, SCL clear_frac≈0.24 |
| Post-khareef | 2026-09-01/2026-09-08 | **insufficient_clear_data** — SCL clear_frac=0.0 (no fabricated NDMI) |

Post-khareef gap is expected near end of Khareef cloud. **Phase-2 default post window widened to late Sep–Oct (`2026-09-15/2026-10-31`)** via `run_mountain_mpi.py` / updated `--post-range` default — fail-honest if still cloudy / not yet ingested; do **not** invent values. Sample GeoJSON is now **stratified** (elev tertile × slope), not first-50.

## Forbidden in GeoJSON properties

`suitability`, `confidence` / ecological confidence, `action` / action ladder, `species` / `species_note`, `mpi` / `mpi_class` / live MPI.

Fog-only *Terminalia dhofarica* remains a **science lock** — this pilot must not invent species fields.

Collection stamps: `status: pilot_unverified`, `layer: mountain_pilot`.

## Known gaps

1. TWI is a coarse uphill-neighbor proxy — not depression-filled D8 / pysheds hydrology.
2. NDMI uses one best scene per window, not a multi-date composite stack.
3. Aspect mean over cells is arithmetic (not circular-mean) — fine for pilot only.
4. DEM mosaic tile edges need visual QA.
5. Default output cell `--grid-m 250` (use `100` for finer local science grids).
6. **No partner UI wire** until science spot-check of this artifact.
7. Full E2E needs Planetary Computer network + `pip install -r requirements.txt`.

## How to run

```bash
cd satellite/pipeline
pip install -r requirements.txt
python run_mountain_pilot.py --dry-run     # schema + empty stub (CI / offline)
python run_mountain_pilot.py               # PC E2E → artifacts/mountain_pilot/
python run_mountain_pilot.py --grid-m 100  # finer local grid (larger geojson)
```

Override output dir: `MOUNTAIN_PILOT_OUT=/path python run_mountain_pilot.py`

## Review checklist

- [x] DEM elev/slope look like Qara escarpment (elev to ~800 m, slope p90 ~27°) — first E2E
- [x] Bbox unchanged at locked values (no nudge needed)
- [x] No forbidden fields in feature properties (asserted in script + checked on E2E)
- [x] Post-khareef NDMI absent where SCL clear_frac insufficient — fail-honest
- [x] Artifacts under `satellite/pipeline/artifacts/` (not imported by UI routes)
- [ ] Science spot-check of sample cells vs field / fog-belt knowledge
- [ ] Still no live MPI / suitability in partner UI (lock held)
- [x] Stratified sample (low/mid/high elev × gentle/steep) — Phase-2
- [x] Phase-2 MPI offline under `artifacts/mountain_pilot/mpi/` (no app/public)
