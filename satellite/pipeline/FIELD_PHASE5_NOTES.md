# Field Loop Phase-5 notes (scaffold / capture)

**Science lock:** `docs/SCIENCE_LOCKS_v0.4_phase5_field_loop.md`  
**Machine twin:** `docs/phase5_field_loop_scaffold.json`  
**Status:** `scientist_locked_pending_ea` — **not** Environment Authority approval.

**EN:** Field log — germination ≠ establishment ≠ survival. Not a platform success score, not an Environment Authority approval.  
**AR:** سجل ميداني — إنبات ≠ تأسيس ≠ بقاء. ليست درجة نجاح للمنصة وليست اعتماداً من هيئة البيئة.

## Domains (never mix)
- `fog_escarpment` — Phase-4 fog six only (`sp-fog-*`)
- `najd_arid` — Phase-4 Najd six only (`sp-najd-*`)

## IDs
- SeedingEvent: `SE-{YYYY}-{NNNNNN}`
- FieldObservation: `FO-{YYYY}-{NNNNNN}` — keep all visits; never overwrite

## Windows (day 0 = event_date)
| visit_type | window |
|------------|--------|
| baseline | −7…0 |
| d30_germination | 21…45 |
| d90_survival | 75…105 |
| d180_establishment | 160…200 |
| d365_survival | 335…395 |
| ad_hoc | any — does **not** close a window |

`window_status`: `on_window` \| `early` \| `late` \| `missed`  
Missed ≠ failure — do not interpolate counts.

## Germination N/A (not zero)
When `establishment_mode` ∈ {protect_regeneration, vegetative_preferred} or  
`method` ∈ {seedling, cutting, wilding, protection_only} or protective interventions →  
`outcome_class=not_applicable` on `d30_germination`.

## Quantity
Optional `{amount, unit, source: operator_reported_unvalidated}` only.  
`campaign_ha` / `seed_kg` / `crew_days` / `kg_per_ha` stay null / forbidden as official.

## Photos / PII
Optional plot evidence. No posed people, **no children**, no ID documents.  
`observer` = team label. `pii_flag`: `none` \| `incidental_person`.  
No face recognition, no auto species ID, no partner photo gallery.

## Hold / OUT
- Mountain partner UI **Hold**
- Artifacts-first — **no** partner Field UI / no `app/public/` write
- No Phase-6 Learning / no auto-rewrite Suitability·Confidence·Site×Species
- No fabricated germination/survival % / no recommendation_success

## Run
```bash
cd satellite/pipeline
python run_field_loop.py
```

## Artifacts
```
satellite/pipeline/artifacts/field/
  seeding_events.sample.json
  field_observations.sample.json
  survival_observations.sample.json   # alias of field_observations
  field_loop.json
  field_events_export.stub.csv
  run_meta.json
```

## Tip-update points (mid-flight Agrofostery locks)
- `engines/field_loop.py` → `validate_seeding_event`, `VISIT_WINDOWS`, `create_planned_followups`
- `docs/phase5_field_loop_scaffold.json` enums
