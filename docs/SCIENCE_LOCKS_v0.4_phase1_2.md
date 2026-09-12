# Science locks — Spec / Roadmap v0.4 Decision Engines (Phase 1 + Phase 2)

**Owner:** Agrofostery Scientist (species / ecology / honesty)  
**Audience:** Programmer + AgriTech  
**Date:** 2026-09-09 (Asia/Muscat)  
**Status:** Binding for Phase 1 coding gates; Phase 2 as specified below  
**Product:** مرصد ظفار الزراعي البيئي | Dhofar Agro & Eco Observatory  

Companion: `docs/ROADMAP_v0.4_decision_engines.md`, Product Spec 1.0.1.

---

## Global honesty (all phases)

1. No confirmed pest/disease/fertilizer diagnosis from satellite.
2. NDMI / MPI / TWI = **proxies**, not plot soil moisture meters.
3. **Data-quality confidence** ≠ **ecological suitability confidence** ≠ **Agricultural Probability**.
4. AOU ≠ Official Farm until cadastral link.
5. Suitability Score and Confidence Score never merged into one number.
6. Fog-escarpment species (*Terminalia dhofarica*, Authority-vetted short list) never auto-mixed with arid Najd species (سدر *Ziziphus spina-christi*, سمر *Vachellia tortilis*, غاف *Prosopis cineraria*).
7. Expert Rules first; ML only after sufficient ground truth (later phase).
8. Every output scene carries: source, acquisition date, product ID, tile, cloud %.

---

## Phase 1 — Agricultural Probability Engine

### 1.1 Output

Per pixel (10–20 m) or per segment after thresholding:

| Field | Type | Meaning |
|-------|------|---------|
| `agricultural_probability` | 0–100 | Likelihood cell is irrigated/cultivated activity |
| `ag_class` | enum | `unlikely` 0–30 · `possible` 30–60 · `likely` 60–80 · `very_likely` 80–100 |
| `data_quality_confidence` | 0–100 | From clear pixels / cloud / coverage only |

### 1.2 Feature set (weights — v1 expert defaults)

All features min–max or z-scored within AOI seasonal window before weighting. Weights sum to 1.0 for the **core optical block**; assists are **gates/boosts**, not equal voters.

**Core optical / temporal (required in Phase 1):**

| Feature | Weight | Notes |
|---------|--------|-------|
| Seasonal / wheat-window NDVI peak (or rolling max NDVI) | 0.22 | Irrigated crops show clear seasonal rise vs desert |
| NDVI temporal persistence (≥ N clear dates above bare floor) | 0.18 | Persistence beats single-date green |
| NDMI mid-season / canopy moisture contrast vs bare desert | 0.15 | Irrigation-like moisture signal |
| SWIR response (B11/B12 brightness; low SWIR with high NDVI) | 0.12 | Crop vs bright soil |
| Red-edge / NDRE (optional if B05–B07 present) | 0.10 | If missing → redistribute weight to NDVI+NDMI |
| Phenology shape (green-up timing vs Najd wheat Nov–Apr **or** year-round fodder pattern) | 0.13 | Two acceptable patterns; both ≠ random desert noise |
| Texture / local variance (edge of pivots/blocks) | 0.10 | Helps rectangular/circular farm structure |

**Bare floor (Najd inland):** NDVI median of known desert cells ≈ 0.05–0.12; use **AOI-relative** bare threshold, default vegetated if NDVI ≥ 0.18 (keep current monitor convention unless recalibrated).

**Assists only (not sole evidence):**

| Assist | Role |
|--------|------|
| **Sentinel-1** VV/VH | Optional boost (+0–5 pts) when optical gaps; never sole “agricultural” label in Phase 1 |
| **Dynamic World** | Assist mask / veto for water/built; **never** sole agricultural label |

### 1.3 Gates (hard)

1. SCL cloud/shadow/cirrus → no probability; nodata.
2. If clear observations in season window < 3 → cap `ag_class` at `possible` and lower `data_quality_confidence`.
3. Single-date NDVI spike alone **cannot** reach `very_likely`.
4. Dynamic World / S1 cannot push class across a tier without optical core support.

### 1.4 Segmentation → AOU candidates

1. Threshold `agricultural_probability` ≥ 60 **or** (`≥ 45` AND persistence gate).
2. Morphological close/open; connected components (4- or 8-connect).
3. Drop components < min area (suggest **≥ 2 ha** for Najd pivots/blocks MVP; tune later).
4. Each component → AOU polygon (see §2).

Grid ~500 m remains **fallback monitoring layer**; Probability Engine is the path to real AOUs.

---

## Phase 1 — AOU identity rules (stable ID)

### 2.1 ID format

`AOU-NJ-{NNNNNN}` zero-padded. Region code `NJ` = Najd; future mountain units use other prefixes (not Phase 1).

### 2.2 Stability across seasons (despite geometry change)

**Matching key (in order):**

1. **Centroid proximity:** candidate centroid within **max(150 m, 0.5 × sqrt(area))** of prior AOU centroid.
2. **IoU** with previous polygon ≥ **0.3** (geometry can drift with detection noise).
3. If multiple matches: highest IoU wins; losers get new IDs.
4. If no match: mint new ID; do **not** reuse retired IDs.
5. Store lineage: `previous_ids[]`, `first_seen_date`, `last_seen_date`, `active` bool.

**Do not** bind ID to fixed 500 m cell index (cells are not identity).

### 2.3 Attributes (Phase 1)

`geometry`, `agricultural_probability` (mean/p50), `data_quality_confidence`, `alert_codes` (map to existing `bare|healthy|water_attention|vigor_attention|unclear` until Stress Scores ship), `area_ha_est`, timestamps, scene citations.

---

## Phase 1–2 — Water / Vigor Stress Scores

Replace peer-only percentiles gradually; **keep four engine codes as UI mapping layer** until scores validated.

### 3.1 Water Stress Score (0–100; higher = more stress)

Inputs (combine; document each term):

| Term | Role |
|------|------|
| **Relative** | NDMI vs vegetated peers same date (current logic) |
| **Historical** | NDMI vs same AOU same DOY ±14d in prior years (if ≥2 prior seasons; else skip) |
| **Persistence** | Stress flag true on ≥2 of last 3 clear observations |
| **Phenology context** | Down-weight “water stress” in expected senescence / post-harvest (Najd wheat Apr–May bare rebound) |
| **Weather context** | Optional ERA5/CHIRPS regional drought — **context only**, never sole driver |

**v1 formula (expert):**  
`W = 0.40*relative + 0.25*historical + 0.25*persistence + 0.10*phenology_penalty`  
Missing historical → renormalize remaining weights.

Map to UI: high W → `water_attention`.

### 3.2 Vigor Stress Score (0–100)

Same structure on **NDVI** (and NDRE if present): relative + historical + persistence + phenology.

Map high V → `vigor_attention` (management / possible nutrient — **not** fertilizer diagnosis).

### 3.3 Healthy / bare

- `bare` if NDVI < bare floor and low probability.
- `healthy` if vegetated and W,V below attention thresholds.
- `unclear` if data_quality_confidence low.

---

## Phase 2 — Biotic Stress Risk (no pest certainty)

### 4.1 Label

**Only:** `possible_biotic_stress` / AR: «إجهاد حيوي محتمل».  
**Forbidden labels:** pest name, disease name, “confirmed infestation”.

### 4.2 Rules (all required for flag)

1. Spatial anomaly: NDVI (or NDRE) distinctly lower than **immediate neighbors** inside same AOU or adjacent AOUs (patch/wedge, not whole-field uniform drought).
2. Temporal: decline faster than phenology expectation and **not** explained by water stress alone (W not dominant or NDMI OK while NDVI crashes).
3. Persistence: anomaly on ≥2 clear dates.
4. Data quality gate: cloud-free enough; else `unclear`.

UI copy must always append field-check recommendation (already in product).

---

## Phase 2 — Moisture Persistence (MPI) curve

### 5.1 Definition

For mountain / restoration cells (and optionally farm AOUs later):

- **T0** = first clear post-onset or post-khareef reference date (documented per season; **dynamic**, not fixed calendar).
- Samples at **T0, T+1w, T+2w, T+4w, T+6w** using clear Sentinel-2 NDMI (and NDWI optional).
- If a week has no clear scene → mark gap; **do not interpolate fabricated NDMI**.
- Curve metric examples: mean NDMI; slope of NDMI over available points; fraction of weeks above AOI dry baseline.

### 5.2 Classes (v1)

| Class | Rule (expert defaults; calibrate later) |
|-------|----------------------------------------|
| **High** | ≥3 valid points; NDMI stays above dry baseline through T+4 or slow decay |
| **Medium** | 2–3 valid points; mixed / moderate decay |
| **Low** | Rapid return to dry baseline by T+2, or only T0 wet |
| **Insufficient** | <2 valid clear points → **no class** (fail-honest) |

Operational weight: prefer **onset + post-khareef** windows over Peak Khareef composites (cloud).

Until validated: UI may show class only with `provisional` / `pilot_unverified` stamp (current honesty).

---

## Phase 2 — Natural Regeneration ladder (action enum)

Order fixed (Spec):

1. Protect Natural Regeneration  
2. Assisted Natural Regeneration  
3. Enrichment Seeding  
4. Active Planting  
5. Avoid / Defer  

**Phase 2 coding:** enum + rule stubs OK; **numeric suitability→action auto-assignment to partners requires field validation** (see Forbidden).

---

## Forbidden until field validation

| Item | Status |
|------|--------|
| Published **Species Suitability Scores** as operational truth | Forbidden |
| Auto **campaign planner** (hectares, seed kg, crew days) as official numbers | Forbidden |
| Pest/disease **names** or certainty | Forbidden |
| Merging Suitability + Confidence into one score | Forbidden |
| Calling MPI / NDMI “soil moisture %” | Forbidden |
| Official farm names without cadastral link | Forbidden |
| Live Khareef “detected onset” without documented EO/climate method + QA | Forbidden |
| ML replacement of Expert Rules without ground-truth report | Forbidden |
| Wiring mountain pilot terrain to partner UI without science re-sign-off | Forbidden (current lock) |
| Mixing Najd dry species onto fog-escarpment recommendations | Forbidden |

**Allowed as provisional / expert-stub (must be labeled):**  
Agricultural Probability v1, AOU IDs, Water/Vigor scores mapped to existing alert codes, Biotic Risk flag with disclaimer, MPI class with provisional stamp, regeneration ladder as **manual/enum display**, Site×Species **matrix scaffold** with Authority-vetted short list but scores marked unvalidated.

---

## Phase coding order (science recommendation)

1. Agricultural Probability + gates + segmentation → AOU minting/identity  
2. Stress Scores (water/vigor) feeding existing four codes  
3. Biotic risk flag  
4. MPI curve + classes (mountain path; fail-honest)  
5. Ladder enum + Site×Species **scaffold only** (no campaign numbers)

---

## Sign-off

Phase 1 gates above are **binding** for Programmer start.  
Phase 2 definitions binding for structure; numeric thresholds marked “calibrate with field data.”  
Questions → Agrofostery Scientist before relaxing Forbidden list.

---

## Phase 3 addendum — Agriculture AOU Suitability / Confidence (2026-09-09)

**Status:** Binding weight locks — `expert_v1_provisional` (NOT `spec_pending`).  
**Owner:** Agrofostery Scientist (weights) + AgriTech (JSON field shapes) + CoS (artifacts-first delivery).  
**Domains must not be mixed with mountain reseeding scores.** `mountain_apply = false`.

### Suitability (`agriculture_aou`) — weights → 0–100

| Term | Weight | Notes |
|------|--------|-------|
| `agricultural_probability / 100` | 0.35 | Phase-1 AgProb |
| NDVI persistence feature | 0.20 | Thin history → weak provisional proxy |
| `(100 − vigor_stress) / 100` | 0.20 | NDVI-based vigor proxy — NOT fertilizer diagnosis |
| `(100 − water_stress) / 100` | 0.15 | NDMI-based moisture proxy — NOT soil moisture % |
| Geometry stability | 0.10 | IoU ≥ 0.3 **or** area ≥ 2 ha → 1.0; else scaled |

Renorm if missing. Stamp `status: expert_v1_provisional`, `suitability_domain: agriculture_aou`, `suitability_summary_label: components_only`.

**AgriTech component shape (required):** `moisture_proxy`, `vigor_proxy`, `phenology_fit`, `terrain_constraint` (+ optional `agricultural_probability_norm`).

### Confidence (`data_evidence`) — weights → 0–100

| Term | Weight | Notes |
|------|--------|-------|
| `data_quality_confidence / 100` | 0.40 | DQ alone ≠ overall confidence |
| `n_clear_dates / 8` (cap 1) | 0.25 | Temporal coverage |
| Historical depth | 0.20 | 0 / 0.5 / 1 for 0 / 1 / 2+ prior seasons |
| Prior IoU | 0.15 | 0 if new ID |

Stamp `confidence_domain: data_evidence`. **Not ecological certainty.**

**AgriTech fields (required):** `data_quality_confidence`, `temporal_coverage_confidence`, `spatial_clarity_confidence`, `overall_confidence`.

### Evidence Gap + Why-this-site + Action ladder

- `evidence_gaps[]` lists missing inputs honestly (no NDRE, no field visit, thin history, no post-khareef clear, no MPI on agriculture AOU, etc.).
- `why_this_site`: `headline`, `drivers`, `cautions`, `recommended_next_step`; **`action_ladder_suggestion` MUST stay `null`** (manual enum only).
- Action ladder = display enum / manual recommended next step only — **no** suitability→action auto-assign.

### Hard gates (Phase 3)

1. **Never merge** Suitability Score + Confidence Score + `data_quality_confidence`.
2. **Do not** apply `agriculture_aou` weights to mountain cells (`mountain_apply=false`).
3. **Do not** write decision artifacts into `app/public/` until science re-sign-off (path: `satellite/pipeline/artifacts/decision/`).
4. **Do not** label MPI as post-khareef when evidence window is onset-T0 only.
5. No campaign numbers, pest names, soil moisture %, live Khareef onset detection.
6. Keep Phase-1 agriculture honesty chrome (AOU ≠ official farm; biotic = risk only).

### Artifacts

```
satellite/pipeline/artifacts/decision/
  aou_suitability_components.json
  aou_confidence.json
  aou_evidence_gaps.json
  action_ladder.stubs.json
  run_meta.json
```

Schemas: `docs/spec_0.4/{suitability_components,confidence,evidence_gap,action_ladder}.schema.json`.

---

## Phase 4 addendum — Seed Intelligence scaffold (2026-09-12)

> **SUPERSEDED (2026-09-12):** Species catalog / domains / vetting for Phase-4 Seed Intelligence are defined only in
> [`docs/SCIENCE_LOCKS_v0.4_phase4_species.md`](SCIENCE_LOCKS_v0.4_phase4_species.md) +
> [`docs/phase4_species_scaffold.json`](phase4_species_scaffold.json)
> (PR #17 remediation). Do **not** re-implement the blocked pre-lock catalog below
> (`pending_agrofostery`, irrigated/fodder placeholder, `agriculture_aou` / `restoration_mountain` as ecological domain ids).
> Historical text retained for audit only.



**Status:** `unvalidated_expert_stub` — matrix / catalog scaffold only (**NOT** operational truth).  
**Owner:** Agrofostery Scientist (species short lists) + AgriTech (JSON field shapes) + CoS (artifacts-first delivery).  
**UI gate:** No Analysis / Restoration / Map Seed panel in the first Phase-4 PR. **No** mountain partner UI. **No** Decision→species candidate wire in partner UI.

### Domains (NEVER mixed)

| Domain | Geography | Starter species (Authority pending) |
|--------|-----------|-------------------------------------|
| `agriculture_aou` | Najd arid / farm AOUs | سدر *Ziziphus spina-christi*, سمر *Vachellia tortilis*, غاف *Prosopis cineraria* + irrigated/fodder **placeholders** labeled unvalidated |
| `restoration_mountain` | Fog-escarpment | *Terminalia dhofarica* (syn. *Anogeissus dhofarica*) **only for now** |

`cross_domain_recommend = false` hard lock. Fog species never auto-mixed onto Najd rows; Najd dry species never onto fog-escarpment rows.

### Field stubs (matrix row)

| Stub | Rule |
|------|------|
| `species_suitability` | `unvalidated` / optional later `expert_v1_provisional` — **not** operational truth |
| `suitability_provisional_0_100` | null OK |
| `seed_recommendation` | `mode: manual` — operator-confirmed only |
| `timing_window` | `calendar_heuristic` + `provisional` — **no** live Khareef onset |
| `seed_provenance` | `local_preferred` flag only |
| `seeding_protocol` | enum steps; `manual_operator_confirmed`; `auto_assign=false` |

**Suitability ≠ Confidence** (unchanged global lock).

### Forbidden (Phase 4)

| Item | Status |
|------|--------|
| Species suitability scores as **operational truth** | Forbidden |
| Auto **campaign planner** fields as official numbers (`campaign_ha`, `seed_kg`, `crew_days`) | Forbidden |
| Mixing `agriculture_aou` ↔ `restoration_mountain` recommend paths | Forbidden |
| Mountain partner Seed / Decision→species UI | Forbidden until post-khareef re-sign-off |
| Pest names / soil moisture % / live Khareef onset | Forbidden (global) |
| Writing seed artifacts into `app/public/` before science re-sign-off | Forbidden |

**Allowed as provisional / expert-stub (must be labeled):** Site×Species matrix scaffold; Authority-pending short lists (`authority_source: pending_agrofostery`); manual protocol enum; offline mountain sample-cell notes.

### Artifacts

```
satellite/pipeline/artifacts/seed/
  species_catalog.json
  site_species_matrix.json
  seed_intelligence.json
  seeding_protocol.stubs.json
  run_meta.json
```

Schemas: `docs/spec_0.4/{species_catalog,site_species_matrix,seed_intelligence}.schema.json`.  
Engines: `engines/seed_intelligence.py` + `run_seed_intelligence.py`.

### Contact before campaigns

Operators **must** contact Agrofostery Authority before any seeding campaign. Placeholder rows are not a planting order.

