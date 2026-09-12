# Science locks — Phase 5 Field Loop

**Owner:** Agrofostery Scientist  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-12 (Asia/Muscat)  
**Status:** Binding for Phase-5 **scaffold / capture** only  
**Product:** مرصد ظفار الزراعي البيئي | Dhofar Agro & Eco Observatory  
**Companions:** `SCIENCE_LOCKS_v0.4_phase4_species.md`, Product Spec 1.0.1 §13–14  
**UI gate:** Mountain partner UI remains **Hold**. No Seed/Field panel on mountain partner map until science re-sign-off.

Machine-readable twin: `docs/phase5_field_loop_scaffold.json`

---

## Honesty (read first)

1. **Germination ≠ establishment ≠ survival.** Never collapse 30 / 90 / 180 / 365 into one “success %”.
2. **Satellite is not a germination meter.** NDVI/NDMI at day 30 may be *context*, never the visit verdict.
3. **A missed visit is not a failure.** Stamp `window_status=missed`. Do not interpolate counts.
4. **One plot does not fail a species.** No auto “Terminalia failed on Qara”.
5. **No fabricated rates.** Do not publish Germination Accuracy / Survival Prediction Accuracy / “63% germination” until n and protocol exist (Spec §14). Example numbers in the brief stay examples.
6. **Operator-reported kg / seed count ≠ campaign planner.** Store what the team said, stamped `operator_reported_unvalidated`. Never treat as official `campaign_ha` / `seed_kg` / `crew_days`.
7. **Phase 5 captures facts. Phase 6 learns.** Field results must **not** auto-rewrite Suitability, Confidence, or Site×Species scores.
8. **Domains never mix.** Event `domain` must match `species_id` domain (`fog_escarpment` | `najd_arid`). Reject otherwise.
9. **Species catalog is the Phase-4 six.** No fodder placeholder, no *Boswellia*, no *P. juliflora*.
10. **Do not print Authority-approved / «معتمد من الهيئة».** `vetting_status` stays `scientist_locked_pending_ea`.
11. **Protect / vegetative interventions** often have **no germination to score**. Use `not_applicable`, not zero.
12. Photos are evidence. They are not an automatic species ID.

---

## 1. Seeding event schema (`SeedingEvent`)

One event = one intervention on one site, one species (or an explicit mix logged as **separate events**). Do not hide a mixed sowing in one row.

| Field | Required | Rule |
|-------|----------|------|
| `event_id` | yes | `SE-{YYYY}-{NNNNNN}` mint, stable |
| `site_ref` | yes | AOU id (`AOU-NJ-…`) or mountain sample / restoration site id |
| `domain` | yes | `fog_escarpment` \| `najd_arid` — must match species |
| `species_id` | yes | One of: `sp-fog-tdhof`, `sp-fog-oleac`, `sp-fog-fsyco`, `sp-najd-zsc`, `sp-najd-vtor`, `sp-najd-pcin` |
| `event_date` | yes | ISO date (Asia/Muscat calendar date) |
| `gps` | yes | lat, lon, optional `accuracy_m` |
| `intervention_type` | yes | `seeding` \| `enrichment_seeding` \| `planting` \| `vegetative` \| `protect_regeneration` \| `assisted_natural_regeneration` |
| `establishment_mode` | yes | inherit catalog default; operator may override with note: `seed` \| `vegetative_preferred` \| `protect_regeneration` |
| `method` | yes | `broadcast` \| `pit` \| `contour` \| `dibble` \| `seedling` \| `cutting` \| `wilding` \| `protection_only` |
| `timing_window` | yes | Fog: `late_khareef` \| `early_post_khareef` \| `deferred`. Najd: `winter_spring_rain` \| `irrigated`. If fog MPI still insufficient, **prefer not to log a go-ahead event** — `deferred` events are records of “we waited”, not plantings. |
| `provenance_class` | yes | `local_same_jabal` \| `regional_dhofar` \| `oman_other` \| `unknown` \| `blocked_exotic` |
| `seed_lot_id` | if seed | optional; unknown lot → `provenance_class=unknown` |
| `quantity` | no | `{ amount, unit, source: operator_reported_unvalidated }` only. Units: `seeds` \| `seedlings` \| `cuttings` \| `grams`. **No** `kg_per_ha` official field. |
| `operator_name` | yes | person or team label |
| `organization` | no | بلدية / متطوعون / وزارة / هيئة / other |
| `n_participants` | no | integer, operator-reported |
| `photos_event` | no | 0–N image refs |
| `notes` | no | free text |
| `khareef_stage` | fog only | catalog stage label if known; else `unknown` |
| `event_status` | yes | `planned` \| `logged` \| `cancelled` |
| `linked_recommendation_id` | no | optional; events may be logged with **no** prior platform recommendation |
| `vetting_status` | yes | `scientist_locked_pending_ea` |

**Reject (do not save as valid):**

- domain ≠ species domain  
- `species_id` not in the six  
- `provenance_class=blocked_exotic`  
- `method=broadcast` on `sp-fog-oleac` or `sp-fog-fsyco` without an override note (catalog: protect / vegetative preferred)  
- missing `event_date` or `gps`  
- fog event dated as a planting while `timing_window=deferred`

**Baseline is not optional in protocol** — it may be missing in data. If missing, first observation still stands; stamp event `baseline_missing=true`.

---

## 2. Observation windows

Clock starts at `event_date` (day 0). Windows are **inclusive**. Visits outside the window are stored, not discarded.

| `visit_type` | Arabic | Center | Window | Meaning |
|--------------|--------|--------|--------|---------|
| `baseline` | خط الأساس | day 0 | day −7 … 0 | Pre-intervention state (or same-day before work) |
| `d30_germination` | إنبات أولي | day 30 | day 21 … 45 | Emergence of **target** seedlings / first leaves |
| `d90_survival` | بقاء قصير | day 90 | day 75 … 105 | Still alive after ~3 months (may still be seedlings) |
| `d180_establishment` | تأسيس متوسط | day 180 | day 160 … 200 | Persisted into / through the first harsh season |
| `d365_survival` | بقاء سنوي | day 365 | day 335 … 395 | Alive after one full year |
| `ad_hoc` | زيارة إضافية | — | any | Extra visit; does **not** close a scheduled window |

`window_status`:

| Value | When |
|-------|------|
| `on_window` | `days_since_event` inside the table |
| `early` | before window open |
| `late` | after window close, before next center |
| `missed` | window closed and **no** visit logged for that `visit_type` |

**Do not** auto-create fake missed rows with counts. A scheduler may list `missed` with `outcome_class=not_observed` only.

**Ecological reading of the clock (do not hard-code as UI copy without the date):**

- Fog, sown late Khareef / early post: **180d ≈ late dry season** (persistence without monsoon). **365d ≈ through the next Khareef.** That is why 180 ≠ 365.
- Najd, sown winter or irrigated: **180d ≈ first summer heat**; **365d ≈ full year including summer.**

If `event_date` is unknown, **no windows** — only `ad_hoc` allowed.

---

## 3. Definitions (binding)

### 3.1 Germination (`d30_germination`)

**Yes:** at least one emerged individual judged to be the **target species** in the plot (radicle/cotyledons/first true leaves, or an obvious seedling).

**No:** bare plot, only non-target seedlings, or observer cannot say.

**Not applicable:** `establishment_mode` is `protect_regeneration` or `vegetative` / `cutting` / `wilding` / `seedling` (already a plant — skip germination, start survival at 90d unless they also sowed seed).

Satellite green-up ≠ germination.

### 3.2 Short survival (`d90_survival`)

Target plant(s) from this event still **alive** at ~90 days. Seedlings count. This is not establishment.

### 3.3 Establishment (`d180_establishment`)

Target plant(s) still alive **and** past the first flush: not only cotyledons; some persistence through the first dry (fog) or first heat (Najd). Spec label: تأسيس متوسط.

If the observer cannot judge “established” vs “still a weak seedling”, use `present_target` + `establishment_uncertain=true`. Do not auto-upgrade.

### 3.4 Annual survival (`d365_survival`)

Target plant(s) from this event still alive at ~one year. First horizon that may later feed Phase-6 learning. Still not a published success rate.

### 3.5 Outcome class (every visit)

| `outcome_class` | Use |
|-----------------|-----|
| `not_observed` | Visit not done / plot not found |
| `not_applicable` | This visit type does not apply (e.g. germination after planting a seedling) |
| `none_detected` | Looked; no target seen |
| `present_uncertain_id` | Something living; species ID unsure |
| `present_target` | Target living (optional `target_count`) |
| `present_nontarget_only` | Other plants only |
| `dead_or_missing` | Previously present, now gone/dead (90/180/365) |
| `protected_only` | Fence / browse control / no new plants expected |

Optional extras (never required to save):

- `target_count` (integer ≥ 0)  
- `subplot_area_m2`  
- `species_id_confidence`: `certain` \| `probable` \| `uncertain`  
- `grazing_sign`, `browse_damage`, `washout`, `drought_note`, `irrigation_on` (Najd), `competition_note`  
- `photos[]`  
- `satellite_context` (NDVI/NDMI scene cite only — not a verdict)

**Forbidden derived fields (Phase 5):**

- `germination_pct` as operational truth  
- `survival_pct` as operational truth  
- `recommendation_success`  
- auto `species_failed` / `site_failed` flags for the engine

If both `target_count` and operator-reported `quantity.amount` (seeds) exist, a **provisional** ratio may be stored as `operator_emergence_ratio_unvalidated` — **never** shown as “germination rate” in partner UI.

---

## 4. Field observation schema (`FieldObservation`)

| Field | Required | Rule |
|-------|----------|------|
| `observation_id` | yes | `FO-{YYYY}-{NNNNNN}` |
| `event_id` | yes | must exist |
| `visit_type` | yes | enum above |
| `visit_date` | yes | ISO date |
| `days_since_event` | yes | integer, computed |
| `window_status` | yes | computed from table |
| `outcome_class` | yes | enum above |
| `observer` | yes | name / team |
| `gps` | no | if plot offset from event gps |
| `target_count` | no | |
| `subplot_area_m2` | no | |
| `species_id_confidence` | no | default `uncertain` if omitted on `present_*` |
| `photos` | no | |
| `notes` | no | |
| `covariates` | no | grazing / browse / washout / drought / irrigation / competition |
| `vetting_status` | yes | `scientist_locked_pending_ea` |

Multiple visits of the same `visit_type` are allowed; keep all. Do not overwrite. A later on-window visit does not delete an early one.


## 4.1 Photos and PII

Photos are **optional plot evidence**, not a required ID check.

| Rule | Lock |
|------|------|
| Subject | Plot, seedlings, soil, browse damage, fence — **not** posed people |
| Faces | Do not require faces. If a person is incidental in frame, that is not a biometric record. **No photos of children.** |
| Identity documents | **Forbidden** (national ID, passport, ministry badge close-up) |
| `observer` | Team / person **label** only — not a civil ID number |
| GPS | Plot coordinates already on the event; photo EXIF GPS optional. Do not store phone-owner name from EXIF |
| Consent | Uploader is the operator; photos are for this observatory’s field log, not a public people gallery |
| Public UI | No partner mountain gallery of field photos until Hold lifts. Operator tool may show the plot image with the field-log disclaimer |
| ML | No face recognition. No auto species ID from the photo in Phase 5 |
| Retention | Keep with the observation row; deleting an event deletes its photos |

`photos[]` item: `{ ref, taken_at?, caption?, pii_flag: none|incidental_person }` — default `none`.

---

## 5. What Phase 5 may show (if any UI)

Allowed internally / operator tools (not mountain partner map):

- Event card + visit timeline  
- Window due / missed (honest)  
- Outcome class labels in AR/EN  
- Disclaimer on every card  

**AR:** «سجل ميداني — إنبات ≠ تأسيس ≠ بقاء. ليست درجة نجاح للمنصة وليست اعتماداً من هيئة البيئة.»  
**EN:** “Field log — germination ≠ establishment ≠ survival. Not a platform success score, not an Environment Authority approval.”

**Not allowed:** mountain partner Field/Seed UI; auto campaign stats; merging visits into one %; rewriting Suitability from one year of logs.

---

## 6. Phase 5 vs Phase 6

| Phase 5 (now) | Phase 6 (later lock) |
|---------------|----------------------|
| Log events + visits | Prediction vs actual |
| Honest missed windows | Calibration sample rules |
| No score rewrite | Model / weight update **after** n and protocol |
| No published accuracy | Accuracy / precision only with declared n |

---

## 7. Forbidden (Phase 5)

- Mixing fog and Najd on one event  
- Adding species outside the six  
- Treating NDVI as germination  
- Filling missed windows with modelled counts  
- Official campaign ha / kg / crew days  
- Publishing survival % or “38% survival” as product truth  
- Auto-updating Site×Species scores from field rows  
- Mountain partner UI  
- *P. juliflora* or *Boswellia* events  
- Claiming هيئة البيئة approval  

---

## Sign-off

**Agrofostery Scientist — 2026-09-12 (Asia/Muscat)**  
Phase-5 Field Loop **locked for scaffold / capture**. Learning and published rates wait for a Phase-6 lock.
