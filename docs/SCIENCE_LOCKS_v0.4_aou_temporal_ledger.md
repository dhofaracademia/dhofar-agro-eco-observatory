# Science locks — AOU Temporal Ledger (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-13 (Asia/Muscat)  
**Status:** Binding honesty + identity lock  
**Verdict: Go-with-fixes**  
**Companions:** `SCIENCE_LOCKS_v0.4_evaluator_endorsement.md` (n_clear / class gates — **unchanged**), `SCIENCE_LOCKS_v0.4_phase1_2.md` §2  
**Machine twin:** `docs/phase_aou_temporal_ledger_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B). Post-khareef MPI `2026-09-15`–`2026-10-31` + pipeline Approve still required.

Evaluator re-review (8.0/10): n_clear=4 / fake `likely` is **RESOLVED** (`85e2467`). Next highest value is a **real per-AOU date ledger**, not new algorithms or datasets.

---

## Historical — RESOLVED (do not re-fix)

**Live fail @ main `5ad4016` (2026-09-13):** window timeseries length (4) and hardcoded `n_clear_dates=4` inflated persistence / `likely`.  
**Resolved @ `85e2467` (PR #22).** Verifying glance: 9/9 `possible`, `n_clear=1`, `persistence_status=single_date_insufficient`.  
Mark the “Live fail” paragraph in `SCIENCE_LOCKS_v0.4_evaluator_endorsement.md` §3 as **Historical / RESOLVED** with that SHA. Do not keep it as an open must-fix.

Class / persistence gates in that file **stand**. This lock only changes **where `n_clear` is counted from**.

---

## P0 — AOU Observation Ledger (required this PR)

### 0. Live fail (2026-09-13, main `1abe9ad`)

`build_observations` starts `obs = []` every run and writes **only the latest** member aggregate. Honesty copy says history “grows as monitor re-runs”; the writer **replaces** it.  
`_aou_scoped_clear_count` uses `first_seen` / `last_seen` / observation date. `assign_aou_ids` hardcodes `n_clear = 1`.

That cannot grow `n_clear` even when real later scenes exist.

### 1. Ledger definition

Store AOU-scoped clear observations in `aou_observations.json` (and the pipeline twin).

| Field | Rule |
|-------|------|
| `observations[]` | **AOU ledger only.** Distinct SCL-clear dates that actually cover **that polygon**. |
| `series_scope` on ledger rows | `aou_members_aggregate` or `aou_direct` — **never** `window_not_aou`. |
| `window_context_series[]` | AOI / timeseries means. `series_scope=window_not_aou`. Context only. **Forbidden** as `n_clear` input. **Forbidden** to copy into `observations[]`. |
| `n_clear_dates` (unit) | Count of **distinct dates** in `observations[]` with valid NDVI. Not first_seen/last_seen. Not a constant. Not `len(timeseries.dates)`. |

Each ledger row: `date`, `product_id`, `tile`, `source`, `cloud_cover`, `ndvi`, `ndmi`, optional `ndre`, `ag_class` / scores for **that date**, `series_scope`. SCL cloud/shadow/cirrus → do not append.

### 2. Append, do not replace

On every `run_ag_probability` / monitor re-score:

1. **Load** existing `aou_observations.json`.  
2. For each AOU, **keep** prior ledger rows (`series_scope != window_not_aou`).  
3. **Upsert** today’s row by `(aou_id, date)` — idempotent re-run of the same date replaces that date only.  
4. **Never** `obs = []` then one latest row.  
5. Rewrite `window_context_series` from `timeseries.json` (context). Keep it **out** of the ledger.

No backfill of window means into the ledger. Optional backfill **only** from cell/AOU-scoped SCL-clear scenes that cover that polygon. Until a second such date exists, `n_clear_dates` stays **1**. That is honest.

### 3. `_aou_scoped_clear_count`

**Must** count distinct ledger dates for that AOU.

**Forbidden sources:** `first_seen_date` / `last_seen_date` alone; hardcoded `1` or `4`; `len(timeseries.dates)`; `window_context_series`.

`assign_aou_ids` re-score: `n_clear = _aou_scoped_clear_count(ledger, aou_id)` **after** the append. Persistence / `likely` gates = evaluator endorsement (n_clear < 2 → persistence null/0, max `ag_class=possible`). Do not invent a new curve.

Per-row `"n_clear_dates": 1` on a single observation is misleading. Put `n_clear_dates` on the **unit**, not as a constant on every row.

### 4. Programmer must-fix (P0)

1. `build_observations`: load + append/upsert; delete `obs = []` wipe.  
2. `_aou_scoped_clear_count`: read the ledger.  
3. Stop hardcoding `n_clear = 1` in `assign_aou_ids` once the ledger is the source (it may still **equal** 1 today).  
4. Decision scaffolds already skip `window_not_aou` — keep that. Re-run Decision after ledger write.  
5. Do not ingest window dates to force n_clear=4.

---

## P1 — same PR or immediate follow (do not skip)

### 5. `active` ≠ “confirmed farm now”

| Field | Meaning |
|-------|---------|
| `active` | Persistent **registry identity** (false only when retired). Not “this is a farm today.” |
| `current_detection` | `detected` / `weak` / `not_detected` on **this run**. |

`detected`: vegetated members this date (NDVI ≥ bare floor and/or `ag_class` in `possible`+).  
`weak`: matched, below vegetation / low probability.  
`not_detected`: identity kept; not seen this run.

AOU ≠ official farm **unchanged**. `active=true` + `not_detected` is allowed. Do not retire an ID because one run missed it.

### 6. Geometry gate ≠ temporal stability

`geometry_stability` may stay as the internal weight key. When `prior_iou` is **null**, Why-this-site / drivers / UI must say **geometry gate (area ≥ 2 ha)** — **not** “geometry stability” and **not** temporal stability.

Current caution “geometry stability uses area gate only” is almost right; lead with **geometry gate**. Driver “Geometry stability (AOU IoU/area gate)” must split: IoU present → stability; IoU null → area gate only.

### 7. Future validation states (do not ship as “validated”)

Keep `najd_model_validation = not_validated` **today**.

Document, do not auto-advance:

| State | Meaning |
|-------|---------|
| `not_validated` | Default. Current product stamp. |
| `pipeline_validated` | Pipeline honesty (n_clear, ledger, disclosure) signed by this role on a SHA — **not** a crop model. |
| `methodology_reviewed` | Named human methodology review. |
| `empirically_validated` | Independent empirical check (HD / known sites / sparse FO / gov layer). |

**Forbidden:** collapsing these into `system_validation_provisional` and calling Najd validated. Programmer does **not** flip the field without a pipeline Approve on that SHA.

---

## Forbidden

| Item | Status |
|------|--------|
| Wipe ledger (`obs=[]` + latest only) | **Forbidden** |
| Window / timeseries dates as AOU `n_clear` or ledger rows | **Forbidden** |
| first_seen/last_seen as the only n_clear source | **Forbidden** |
| Relax class/persistence gates because the ledger exists | **Forbidden** |
| `active=true` narrated as confirmed farm | **Forbidden** |
| Area≥2ha called temporal / geometry “stability” when `prior_iou` is null | **Forbidden** |
| Marking evaluator live-fail still open after `85e2467` | **Forbidden** |
| Mountain seeding recs; onset MPI as post-khareef | **Forbidden** (Hold) |

---

## Mountain

**Unchanged.** 3.B seeding-rec Hold until post-khareef MPI + pipeline Approve on that run.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-13 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** P0 ledger append is required. P1 in the same or immediate follow PR. Persistence / likely rules unchanged. Mountain Hold unchanged.
