# Seed Phase-4 notes — Site × Species scaffold (v0.4)

**Status:** `unvalidated_expert_stub` — offline artifacts only.  
**UI gate:** Analysis / Restoration / Map Seed panels **deferred** (artifacts-first PR). **No** mountain partner Seed UI. **No** Decision→species wire in partner UI.  
**Never write** to `app/public/` until science re-sign-off.

**Binding:** `docs/SCIENCE_LOCKS_v0.4_phase1_2.md` §Phase4 + Forbidden table.  
**Roadmap:** `docs/ROADMAP_v0.4_decision_engines.md` §35 مرحلة 4 — Seed Intelligence.

## Domains (never mixed)

| Domain | Sites | Species starter rows |
|--------|-------|----------------------|
| `agriculture_aou` | Najd AOU registry (`AOU-NJ-######`) | سدر *Ziziphus spina-christi*, سمر *Vachellia tortilis*, غاف *Prosopis cineraria*, irrigated/fodder placeholder |
| `restoration_mountain` | MPI sample cells (`MPI-SAMPLE-…`) offline only | *Terminalia dhofarica* (syn. *Anogeissus dhofarica*) only |

`authority_source: pending_agrofostery` until Authority short list lands.

## Scripts

| Script | Role |
|--------|------|
| `run_seed_intelligence.py` | Read AOU registry + MPI sample → seed artifacts |
| `engines/seed_intelligence.py` | Catalog + domain-separated matrix builders + protocol stubs |

## Artifact paths

```
satellite/pipeline/artifacts/seed/
  species_catalog.json
  site_species_matrix.json
  seed_intelligence.json
  seeding_protocol.stubs.json
  run_meta.json
```

Schemas: `docs/spec_0.4/{species_catalog,site_species_matrix,seed_intelligence}.schema.json`.

## Matrix min fields

`site_ref`, `domain`, `species_id`, `species_name_sci`, `suitability_provisional_0_100` (null OK), `status: unvalidated_expert_stub`, `evidence_gaps`.

Field stubs per row: `species_suitability`, `seed_recommendation` (manual), `timing_window` (calendar heuristic provisional), `seed_provenance` (`local_preferred`), `seeding_protocol` (enum steps, operator-confirmed).

## Hard gates

| Gate | Value |
|------|-------|
| `never_mix_domains` | true |
| `suitability_neq_confidence` | true |
| Campaign fields (`campaign_ha`, `seed_kg`, `crew_days`) | **absent** — not official numbers |
| `auto_assign` / auto campaign planner | false |
| Mountain partner UI | false |
| Writes to `app/public/` | false |
| Live Khareef onset / pest / soil moisture % | forbidden |

## Inputs (read-only)

- `app/public/data/aou/aou_registry.json`
- `satellite/pipeline/artifacts/mountain_pilot/mpi/mpi_cells.sample.geojson`

## Run

```bash
cd satellite/pipeline
python3 run_seed_intelligence.py
```

## What Seed Intelligence does / does not

**Does (scaffold):** domain-separated species catalog; Site×Species matrix with null/unvalidated scores; manual protocol enum; offline mountain sample notes; Authority-contact stamp.

**Does not:** operational suitability truth; campaign ha / seed kg / crew days; Analysis or Restoration Seed UI; mountain partner Decision→species recommendations; pest certainty; soil moisture %; live Khareef onset; cross-domain recommend.

**Before campaigns:** contact Agrofostery Authority.

## Done-when (artifacts PR)

1. Schemas under `docs/spec_0.4/` for species_catalog / site_species_matrix / seed_intelligence.
2. Engines + runner produce artifacts under `artifacts/seed/` with unvalidated stamp.
3. Domains separated; zero cross-domain rows.
4. No campaign quantity fields; no Seed UI; no mountain partner UI; no `app/public/` seed writes.
5. README + SCIENCE_LOCKS §Phase4 + this notes file.
6. Base: main after PR #15 (`87b1631…`).
