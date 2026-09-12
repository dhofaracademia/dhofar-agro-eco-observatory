# Science locks — Phase 6 Learning

**Owner:** Agrofostery Scientist  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-12 (Asia/Muscat)  
**Status:** Binding for Phase-6 **scaffold only**  
**Product:** مرصد ظفار الزراعي البيئي | Dhofar Agro & Eco Observatory  
**Companions:** Phase-4 species lock, Phase-5 field loop, Product Spec 1.0.1 §14  
**UI gate:** Mountain partner UI remains **Hold**.

Machine-readable twin: `docs/phase6_learning_scaffold.json`

**Verdict for this phase: Go** — join pairs + count tables + narrative annual template. **No** live weight writes. **No** published %.

---

## Honesty (read first)

1. Phase 6 **joins** predictions to field visits. It does **not** invent germination/survival %.
2. `missed` / `not_observed` is a **coverage gap**, not a zero and not a failure.
3. `not_applicable` germination is **excluded** from germination learning (not success, not fail).
4. One plot does **not** fail a species or a site. No auto `species_failed` / `site_failed`.
5. **expert_v1 weights stay frozen** in operational engines. Phase 6 must not rewrite AgProb, stress, MPI, Suitability, Confidence, or Site×Species scores.
6. Spec §14 metrics (Accuracy, Germination Accuracy, Survival Prediction Accuracy, …) stay **named, empty, and forbidden to fill** until a later lock + declared n.
7. Domains never mix in one calibration pool. Species stay the Phase-4 six.
8. Prediction snapshots that were `unvalidated` stay labeled unvalidated. An unvalidated stub is not a “model forecast”.
9. No Authority-approved / «معتمد من الهيئة».
10. Annual report is a **narrative template**, not a scorecard.

---

## 1. Prediction vs actual (join)

### 1.1 Join key

One `LearningPair` = one `SeedingEvent` × one **eligible** `FieldObservation` at one horizon.

| Field | Rule |
|-------|------|
| `pair_id` | `LP-{YYYY}-{NNNNNN}` |
| `event_id` | required, must exist |
| `observation_id` | required, must exist, same event |
| `horizon` | `d30_germination` \| `d90_survival` \| `d180_establishment` \| `d365_survival` |
| `domain` | copied from event; must match species |
| `species_id` | Phase-4 six only |

Do **not** join across events. Do **not** roll four horizons into one pair.

### 1.2 Prediction snapshot (what we thought *before* / at event)

Taken from the event + any linked recommendation. If none, say so.

```
prediction: {
  linked_recommendation_id,          # null OK
  suitability_stub,                  # null or unvalidated number
  suitability_status: unvalidated_stub | none,
  timing_window,
  intervention_type,
  establishment_mode,
  provenance_class
}
```

Never back-fill a suitability number after the field visit. If it was null at event time, it stays `none`.

### 1.3 Actual (what the field said)

```
actual: {
  visit_type,          # = horizon
  visit_date,          # required for eligible
  days_since_event,
  window_status,       # on_window | late  (see eligibility)
  outcome_class,       # present_target | none_detected | dead_or_missing | present_uncertain_id
  target_count,        # optional
  species_id_confidence
}
```

### 1.4 Eligibility (who enters the pair table)

A visit is **eligible** only if **all** are true:

1. `visit_date` is present (a real visit).  
2. `window_status` is `on_window` **or** `late`.  
3. `outcome_class` ∈ {`present_target`, `none_detected`, `dead_or_missing`, `present_uncertain_id`}.  
4. Horizon matches `visit_type`.  
5. For `d30_germination`: **exclude** `not_applicable` (protect / vegetative / seedling). Those events simply have **no germination pair**.

**Never eligible:**

- `window_status=missed`  
- `outcome_class=not_observed`  
- `outcome_class=not_applicable`  
- `window_status=early` (too soon to count)  
- interpolated / scheduler stubs without `visit_date`

`present_uncertain_id` is eligible but must be **separated** in counts (`n_uncertain`), never pooled into present_target.

### 1.5 What you may store as “comparison”

Per horizon × domain × species (and overall-with-n):

| Allowed | Forbidden |
|---------|-----------|
| `n_events` | `germination_pct` as operational truth |
| `n_eligible_pairs` | `survival_pct` as operational truth |
| `n_present_target` | `recommendation_success` |
| `n_none_detected` | `accuracy` / precision / recall filled |
| `n_dead_or_missing` | `survival_prediction_accuracy` filled |
| `n_uncertain` | one rolled-up “success %” |
| `n_missed_windows` (coverage) | treating missed as zero |
| `n_not_applicable` (coverage) | treating N/A as fail |

If someone wants a fraction later: only `count_ratio_unvalidated = n_present_target / n_eligible_pairs` with **both counts shown**, `n` declared, and **never** labeled germination rate / survival rate in UI. **Phase-6 scaffold: do not even emit that fraction.** Counts only.

Satellite NDVI at the visit is optional `context`, never the actual.

---

## 2. Calibration vs frozen expert_v1

| Engine | Phase-6 status |
|--------|----------------|
| Agricultural Probability weights | **Frozen** `expert_v1` |
| Water / Vigor stress weights | **Frozen** |
| MPI class rules | **Frozen** |
| AOU Suitability / Confidence weights | **Frozen** |
| Site×Species scores | Stay `unvalidated` — **no write** |
| Species short list | Frozen (Phase-4 six) |

**Allowed in scaffold:**

- `calibration_status = frozen_expert_v1`  
- `proposed_change[]` rows with `status: not_authorized` and **empty** `delta`  
- A `thin_n` flag when `n_eligible_pairs` < threshold (below)

**Not allowed in this phase:**

- Writing new weights to engines  
- Auto-tuning from the 3 sample events (or any n below threshold)  
- ML models  
- Pooling fog + Najd to “get n up”

### `calibration_pool` flag

`calibration_pool=true` is **not** grouping identity alone. Identity is `species_id × domain × horizon`. Emit `calibration_pool=true` only when that identity **and** `n_eligible_pairs ≥ 20`. Thin rows keep identity in `group` with `calibration_pool=false` + note `grouping_identity_only`.

### Future unlock (not this PR — record only)

A **later** science lock may allow a *draft* `proposed_delta` when **all** hold:

- `n_eligible_pairs` ≥ **20** for that `species_id × domain × horizon`  
- Horizon for restoration learning is **d365_survival** first (d180 second). Do not unlock weights from d30 alone.  
- Suitability calibration (if ever): need pairs in more than one suitability bin.  
- Agrofostery Scientist sign-off.  
- Still no partner UI auto-apply.

Until then, Spec §14 metric names may appear as **empty slots** (`value: null`, `reason: insufficient_n`).

---

## 3. Annual restoration report

**Narrative template only.** Offline artifact. Not a mountain partner report.

Suggested sections (bilingual):

1. Year + Khareef stage notes (facts, no live onset claim)  
2. Events logged (n by domain, species, intervention)  
3. Visit coverage (n eligible / n missed / n N/A by horizon)  
4. Outcome **counts** by horizon × domain × species  
5. Qualitative notes (grazing, washout, drought, irrigation) — from covariates, not invented  
6. Honesty box: insufficient n; weights frozen; not EA approval  
7. Empty “metrics reserved” table (Accuracy, …) all null  

**Forbidden in the report:** filled success %, “Terminalia failed”, campaign ha/kg, Authority-approved, merging Suitability+Confidence, using sample FO stubs as if they were real 2025/26 field campaigns without labeling `scaffold_sample`.

Current Phase-5 samples are **scaffold**. The first annual report must stamp `sample_rows_not_a_season`.

---

## 4. Schema notes (for Programmer)

```
LearningPair
  pair_id, event_id, observation_id, horizon
  domain, species_id
  prediction{}          # snapshot; no back-fill
  actual{}              # eligible visit only
  eligible_for_calibration: true
  vetting_status: scientist_locked_pending_ea

LearningCounts          # raw n only, no percents
  group: {horizon, domain, species_id}
  n_events, n_eligible_pairs, n_present_target,
  n_none_detected, n_dead_or_missing, n_uncertain,
  n_missed_windows, n_not_applicable

CalibrationLedger
  calibration_status: frozen_expert_v1
  proposed_change[]: { engine, status: not_authorized, delta: null }

AnnualReportStub
  year, narrative_sections[], metrics_reserved[] (all null)
  stamp: narrative_template_only
  sample_rows_not_a_season: true | false
```

Join path: `SE-*` → `FO-*` where `FO.event_id = SE.event_id` and eligibility holds. No orphan pairs.

---

## 5. Forbidden (Phase 6)

- Auto `species_failed` / `site_failed`  
- Rewriting Suitability / Confidence / Site×Species from sparse plots  
- Mountain partner UI / partner Learning dashboard  
- Filling Spec §14 accuracy metrics  
- `germination_pct` / `survival_pct` operational fields  
- Treating missed or N/A as zeros  
- Mixing domains in one pool  
- Back-filling prediction suitability after the visit  
- Live weight writes / ML  
- Campaign planner numbers  
- «معتمد من الهيئة» / Authority-approved  

---

## Sign-off

**Agrofostery Scientist — 2026-09-12 (Asia/Muscat)**  
**Go** for Phase-6 scaffold: pairs + counts + frozen ledger + narrative report.  
Model improvement and published rates wait for a later lock + n.
