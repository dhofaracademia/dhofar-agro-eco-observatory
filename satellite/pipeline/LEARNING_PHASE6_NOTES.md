# Learning Phase-6 notes (scaffold / join)

**Science lock:** `docs/SCIENCE_LOCKS_v0.4_phase6_learning.md`  
**Machine twin:** `docs/phase6_learning_scaffold.json`  
**Status:** `scientist_locked_pending_ea` — **not** Environment Authority approval.  
**Calibration:** `frozen_expert_v1` — no live weight writes.

**EN:** Learning scaffold — joins and counts only. Not a published success rate, not an Environment Authority approval. Weights remain frozen expert_v1.  
**AR:** مسودة تعلّم — ربط وعدّ فقط. ليست نسبة نجاح منشورة وليست اعتماداً من هيئة البيئة. الأوزان تبقى expert_v1 مجمّدة.

## Join (LP-{YYYY}-{NNNNNN})
One `SeedingEvent` × one **eligible** `FieldObservation` at **one** horizon. Do not roll four horizons into one pair.

Eligible only if **all** hold:
1. `visit_date` present (real visit)
2. `window_status` ∈ {`on_window`, `late`}
3. `outcome_class` ∈ {`present_target`, `none_detected`, `dead_or_missing`, `present_uncertain_id`}
4. Horizon = `visit_type`
5. `d30_germination` **excludes** `not_applicable`

**Never eligible:** `missed` · `not_observed` · `early` · `not_applicable` · undated scheduler stub.

`present_uncertain_id` is counted in `n_uncertain` — **never** pooled into `n_present_target`.

Prediction snapshot: no back-fill of suitability after the visit. If it was null at event time, `suitability_status=none`.

Id-only coverage links (`id_joins`) record SE ↔ FO ↔ optional `aou_id`/`site_ref` ↔ optional recommendation id for every learning-horizon FO, including ineligible stubs.

## Counts allowed (raw n only)
`n_events` · `n_eligible_pairs` · `n_present_target` · `n_none_detected` · `n_dead_or_missing` · `n_uncertain` · `n_missed_windows` · `n_not_applicable`

**Forbidden:** `germination_pct` / `survival_pct` / `recommendation_success` / filled Spec §14 accuracy · one rolled-up success % · `count_ratio_unvalidated` in this scaffold.

Phase-5 samples are **undated stubs** → `n_eligible_pairs=0`. Stamp `sample_rows_not_a_season`.

## Ledger
`calibration_status=frozen_expert_v1`.  
`proposed_change[]`: `status=not_authorized`, `delta=null`, `proposed_change={}`, `auto_apply=false`, `requires=[agrofostery_approve, cos_gate]`.  
No fog+Najd pooling. No live engine writes.

**Future unlock (NOT this PR):** `n_eligible_pairs` ≥ 20 per `species_id × domain × horizon`; d365 first, d180 second; no unlock from d30 alone; Agrofostery sign-off.

## Annual report
Narrative template only + outcome_class counts.  
`stamp=narrative_template_only` · `unpublished_scaffold=true` · `sample_rows_not_a_season=true` when using Phase-5 samples.  
Spec §14 metric names appear as empty slots (`value: null`, `reason: insufficient_n`).

Export stub: `annual_report.export.stub.md` + `.csv` — **not** a campaign planner.

## Hold / OUT
- Mountain partner UI **Hold**
- **No** Learning UI / partner dashboard / `app/public/` write
- No auto `species_failed` / `site_failed`
- No Suitability / Confidence / Site×Species rewrite
- No published %
- No auto-apply of calibrated weights

## Optional operator note (read-only; no UI this PR)
An experimental operator dashboard **may later** list `pair_id` / raw counts / ledger `not_authorized` status as **read-only**.  
It **must** stamp `experimental` / `unvalidated`, **must not** show germination/survival %, **must not** auto-apply weights.  
Partner Learning dashboard remains **forbidden**. Mountain UI remains **Hold**. This PR ships **no UI**.

## Run
```bash
cd satellite/pipeline
python run_learning_loop.py
```

## Artifacts
```
satellite/pipeline/artifacts/learning/
  prediction_field_joins.sample.json
  calibration_ledger.json
  annual_report.template.json
  annual_report.export.stub.md
  annual_report.export.stub.csv
  model_improvement_log.json
  run_meta.json
```

## Tip-update points (mid-flight Agrofostery locks)
- `engines/learning_loop.py` → `load_scaffold`, `ineligible_reason`, `build_learning_pair`, `build_calibration_ledger`, `build_annual_report`
- `docs/phase6_learning_scaffold.json` enums / future unlock thresholds
