# Spec 0.4 — Phase-1 agricultural + Phase-2 mountain evidence + Phase-3 decision + Phase-4 seed schemas

Binding science: [`docs/SCIENCE_LOCKS_v0.4_phase1_2.md`](../SCIENCE_LOCKS_v0.4_phase1_2.md)  
Roadmap: [`docs/ROADMAP_v0.4_decision_engines.md`](../ROADMAP_v0.4_decision_engines.md)

These JSON Schemas describe **Phase-1 Agriculture**, **Phase-2 mountain evidence**, **Phase-3 Decision Engine**, and **Phase-4 Seed Intelligence** contracts. Species scores as operational truth, campaign numbers, live MPI/Khareef detection, pest certainty, and partner mountain decision / Seed UI remain **out of scope / forbidden**.

## Field → SCIENCE_LOCKS mapping

| Schema file | SCIENCE_LOCKS section | Notes |
|-------------|----------------------|-------|
| `agricultural_probability.schema.json` | §1 Agricultural Probability Engine | Weights + gates; NDRE renorm when unavailable |
| `aou_identity.schema.json` | §2 AOU identity rules | `AOU-NJ-{NNNNNN}`; centroid + IoU≥0.3; never cell index |
| `aou_observation.schema.json` | §2.3 + §3 attributes@T | Separates identity from geometry/observation/probability/area @T |
| `stress_scores.schema.json` | §3 Water / Vigor Stress | 0.40 / 0.25 / 0.25 / 0.10; renorm if no history |
| `biotic_risk.schema.json` | §4 Biotic Stress Risk | `possible_biotic_stress` only — never pest name |
| `moisture_persistence.schema.json` | §5 Moisture Persistence (MPI) | Offline mountain curve + classes; gaps=null; provisional |
| `natural_regeneration_ladder.schema.json` | §6 Natural Regeneration ladder | Enum + rule stubs only — **no** suitability→action auto-assign |
| `suitability_components.schema.json` | §Phase3 Suitability | `agriculture_aou` components; `expert_v1_provisional`; never merge |
| `confidence.schema.json` | §Phase3 Confidence | `data_evidence`; ≠ Suitability ≠ DQ alone; not ecological certainty |
| `evidence_gap.schema.json` | §Phase3 Evidence Gap | Honest missing-input list |
| `action_ladder.schema.json` | §Phase3 Action ladder | Display enum / manual only; `action_ladder_suggestion` null |
| `species_catalog.schema.json` | §Phase4 Seed catalog | Domain-separated short lists; `authority_source: pending_agrofostery` |
| `site_species_matrix.schema.json` | §Phase4 Site×Species | `unvalidated_expert_stub`; null scores OK; no campaign fields |
| `seed_intelligence.schema.json` | §Phase4 Wrapper | Protocol stubs + UI gates (all false in scaffold PR) |

## Phase-2 mountain evidence (offline only)

- Artifacts live under `satellite/pipeline/artifacts/mountain_pilot/` (incl. `mpi/`).
- **Never** write MPI / ladder into `app/public/` until science re-sign-off (Forbidden table).
- NDMI / MPI = moisture **proxies**, not soil moisture %.
- MPI classes require ≥2 valid clear points; else `Insufficient` / no class (fail-honest).
- Prefer onset + post-khareef (late Sep–Oct) over Peak Khareef composites.
- **Onset labeling lock:** if T0 is onset-window fallback, stamp `evidence_window: onset` / `product_kind: onset_window_dry_mpi_provisional`. Do **not** label as post-khareef. Low ≠ failed post-khareef recovery.

## Phase-3 Decision Engine (offline artifacts)

- Engines: `satellite/pipeline/engines/{suitability,confidence,evidence_gap}.py`
- Runner: `satellite/pipeline/run_decision_scaffolds.py`
- Artifacts: `satellite/pipeline/artifacts/decision/` — **NOT** `app/public/` until science re-sign-off
- Domains: `suitability_domain: agriculture_aou`, `confidence_domain: data_evidence`
- Gates: `never_merge=true`, `mountain_apply=false`, `action_auto_assign=false`
- AgriTech component shape: `moisture_proxy`, `vigor_proxy`, `phenology_fit`, `terrain_constraint` + `suitability_summary_label: components_only`
- Confidence shape: `data_quality_confidence` / `temporal_coverage_confidence` / `spatial_clarity_confidence` / `overall_confidence`
- `why_this_site.action_ladder_suggestion` **MUST** stay `null` (manual enum only)
- Analysis Decision UI chrome deferred to a later PR

### Locked weights (expert_v1_provisional)

**Suitability (agriculture_aou):** ag_probability 0.35 · NDVI persistence 0.20 · inverse vigor 0.20 · inverse water 0.15 · geometry stability 0.10 (renorm if missing).

**Confidence (data_evidence):** data_quality 0.40 · n_clear_dates/8 0.25 · historical depth 0.20 · prior IoU 0.15.

## NDRE (AgriTech STAC prefs)

- **Primary:** `NDRE = (B08 − B05) / (B08 + B05)` on PC Sentinel-2 L2A.
- **Documented fallback only:** if B05 missing, try B06 then B07 (record `ndre_band`).
- **No silent third formula.** If no red-edge band → omit NDRE (`ndre: null`, `ndre_available: false`) and redistribute AgProb weight 0.10 → NDVI peak + NDMI.
- SCL cloud/shadow/cirrus gates apply **before** indices.
- **SWIR:** prefer `swir_feature` from B11/B12 brightness on the STAC path; NDVI+NDMI proxy only when SWIR bands unavailable.

## Runtime artifacts (`app/public/data/`)

| Path | Role |
|------|------|
| `latest_alerts.geojson` | Monitoring grid (+ optional `aou_id`, stress, ag_probability, ndre) |
| `timeseries.json` | Window-level series (kept) |
| `meta/last_refresh.json` | Stamp |
| `aou/aou_registry.geojson` | Persistent AOU polygons + identity fields |
| `aou/aou_observations.json` | Per-AOU time series |

500 m grid remains **fallback / debug** monitoring layer; Probability Engine → segmented AOUs is the product path.

Decision scaffolds intentionally live under `satellite/pipeline/artifacts/decision/` (not `app/public/`) until science re-sign-off.

## Phase-4 Seed Intelligence (offline artifacts)

- Engines: `satellite/pipeline/engines/seed_intelligence.py`
- Runner: `satellite/pipeline/run_seed_intelligence.py`
- Artifacts: `satellite/pipeline/artifacts/seed/` — **NOT** `app/public/` until science re-sign-off
- Domains: `agriculture_aou` (Najd) vs `restoration_mountain` (fog-escarpment) — **never mixed**
- Starter rows: سدر / سمر / غاف (+ irrigated-fodder placeholder) · *Terminalia dhofarica* (syn. *Anogeissus dhofarica*)
- Status: `unvalidated_expert_stub`; `suitability_provisional_0_100` may be null
- Gates: no campaign_ha/seed_kg/crew_days; manual protocol only; no Analysis/Restoration Seed UI; no mountain partner UI
- Contact Agrofostery Authority before any campaign (`authority_source: pending_agrofostery`)

## Later phases

Field/Learning remain ROADMAP later. Partner mountain UI + Seed UI remain Forbidden until re-sign-off.
