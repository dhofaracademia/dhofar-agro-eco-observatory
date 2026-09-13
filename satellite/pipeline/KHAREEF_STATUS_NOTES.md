# Khareef Status Tracker — Samhan → Sarfait (fog_escarpment)

**Binding:** `docs/SCIENCE_LOCKS_v0.4_khareef_status_tracker.md`  
**Scaffold:** `docs/phase_khareef_status_tracker_scaffold.json`  
**Schema:** `docs/spec_0.4/khareef_status.schema.json`

## What this is

3.A **status tracker** for vegetation / canopy-moisture indicators along the fog corridor.  
**Not** a seeding map. **Not** plant-here. **3.B seeding-rec Hold unchanged.**

Partner copy (EN): “Khareef status — vegetation and moisture indicators. Not a seeding recommendation.”  
AR: «حالة الخريف — مؤشرات غطاء ورطوبة. ليست توصية بذر.»

## Scripts / artifacts

| Path | Role |
|------|------|
| `run_khareef_status.py` | Corridor segments + status cells + run_meta |
| `artifacts/khareef_status/run_meta.json` | Per-segment WGS84 bboxes + stage / product_kind honesty |
| `artifacts/khareef_status/khareef_status_cells.geojson` | Status sample cells (preferred name) |
| `artifacts/khareef_status/corridor_segments.geojson` | Segment envelopes |
| `app/public/data/mountain/khareef_status_cells.geojson` | Partner UI mirror |

Reuses Qara mountain MPI meta when present (`onset_window_dry_mpi_provisional`). Other segments fail-honest `insufficient` until SCL-clear S2 + Approve.

## Stage / product_kind (2026-09-13 Asia/Muscat)

- `khareef_stage`: `late_khareef` (calendar heuristic) or `insufficient` per segment — **not** `post_khareef`.
- `product_kind`: `onset_window_dry_mpi_provisional` (Qara reuse) or `insufficient`.
- Post window opens **2026-09-15**; `post_khareef` / `post_khareef_mpi` only after clear scene + pipeline Approve.

## Domain

`fog_escarpment` only. Never mix `najd_arid` / Najd AOUs.

## How to run

```bash
cd satellite/pipeline
python run_khareef_status.py --dry-run
KHAREEF_STATUS_ASOF=2026-09-13 python run_khareef_status.py
```
