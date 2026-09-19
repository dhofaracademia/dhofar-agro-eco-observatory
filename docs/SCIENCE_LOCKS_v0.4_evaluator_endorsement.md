# Science locks — Evaluator endorsement + n_clear honesty (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-13 (Asia/Muscat)  
**Status:** Binding honesty + classifier lock  
**AI pipeline Go-with-fixes** (not independent human expert sign-off)  
**Companions:** `SCIENCE_LOCKS_v0.4_satellite_first.md`, `SCIENCE_LOCKS_v0.4_phase1_2.md` §1.3 / Phase-3 Confidence  
**Machine twin:** `docs/phase_evaluator_endorsement_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B). Post-khareef MPI window `2026-09-15`–`2026-10-31` + my SHA still required.

Evaluator accepted product philosophy after the user’s clarification:

> Satellite-first, evidence-aware, field-optional — scientifically validated at the **system** level.

This file locks that distinction, the partner UX framing, and the **required** single-date persistence fix. It does **not** make field visits a prerequisite. It does **not** declare the Najd model validated.

---

## 1. Two different “validations” (do not collapse)

| Layer | Who | Required to use Analysis / Decision / Seed? | What it means |
|-------|-----|-----------------------------------------------|---------------|
| **Stakeholder field verify** | Partner / farmer / volunteer, per AOU | **No.** Optional. Not every AOU. Not a UX gate. | A dated Field Observation *enhances* evidence on that unit. Absence is an honesty chip, never a red lock. |
| **Platform scientific validation** | Agrofostery Scientist + periodic methodology checks | **Yes, at the system level** — independent of whether any partner filed an FO. | The *method* (indices, gates, n_clear, class caps, stamps) is reviewed. This is **not** “9 AOUs exist, therefore Najd is validated.” |

**Forbidden claim:** “satellite-first + 9 AOUs = Najd model scientifically validated.”  
**Allowed stamp today:** `provisional_satellite_analytical_service` / «خدمة تحليلية مؤقتة من القمر الصناعي».  
**Validation status field (system, not per-AOU):** `najd_model_validation = not_validated` until I sign a written methodology check (see §5).

Satellite-first (no FO prerequisite) **stands**. Field-optional is about the *partner*. System validation is about *us*.

---

## 2. Partner UX — evidence level, not “Field optional” as the lead line

Prefer this chrome over repeating “Field optional” / “a field visit is not required” as the primary honesty sentence. That line stays **true** and may appear once as a footnote. It must not be the product’s first scientific claim.

### 2.1 Evidence level (per AOU, required)

| `evidence_level` | When |
|------------------|------|
| `satellite_only` | Default. No dated eligible FO on this AOU. **All 9 current Najd AOUs.** |
| `enhanced_by_field_verification` | Only when a **dated** eligible Field Observation exists for that AOU (Phase-5 windows). |

AR labels: «قمر فقط» · «معزّز بتحقق ميداني».  
EN labels: `Satellite-only` · `Enhanced by field verification`.

### 2.2 Show together (Decision / Analysis card)

1. **Confidence** (`data_evidence`, 0–100, separate from Suitability).  
2. **Evidence basis** (chips, not a merged score), for example:
   - Satellite: Sentinel-2 L2A · date list · `n_clear_dates=N`
   - Historical: Not available / `K` prior seasons
   - Field verification: Not available · or FO date + role
3. **Product stamp** when a claim would overreach: `Provisional satellite-based analytical service` / «خدمة تحليلية مؤقتة من القمر الصناعي».

### 2.3 Optional CTA (never a gate)

“Add field observation” / «أضف ملاحظة ميدانية» → upgrades `evidence_level` to `enhanced_by_field_verification` and may later join Learning.  
**Not** a prerequisite. **Not** “next required step.” Missing FO stays `caution`, never `blocking`.

### 2.4 Copy that must change

Lead with evidence level + stamp. Demote “field visit is not required / معاينة ميدانية لاحقة اختيارية…” to one secondary line.  
**Still forbidden:** «يجب المعاينة الميدانية قبل الاستخدام» / “field visit required before acting.”

---

## 3. Required fix — `n_clear` is AOU-scoped, never the window count

**Live fail (2026-09-13 glance, main `5ad4016`) — Historical / RESOLVED @ `85e2467` (PR #22):**

- All 9 Najd AOUs have **one** AOU-scoped observation: `2026-09-06`.
- `timeseries.json` has **four** AOI-window dates (2026-08-17, 08-25, 08-30, 09-06). Those are *area* composites, not per-AOU clears.
- `run_ag_probability.py` `assign_aou_ids` hardcodes `n_clear_dates=4`, `persistence_feature=0.5`.
- `main()` sets `n_clear = len(timeseries.dates)` (4) and `enrich_features` treats a vegetated cell as green on `min(n_clear, 3)` window dates.
- Result: four AOUs stamped `likely` (prob 61–65). Phase 1.3 already says `<3` clear → cap at `possible`. The gate was bypassed by a fake 4.

**This is the evaluator’s point.** One clear date must not become four. Strong temporal persistence must not be asserted from a single date.

### 3.1 Definitions (binding)

| Field | Meaning |
|-------|---------|
| `n_clear_dates` | Count of **distinct dates** with SCL-clear, valid NDVI **on that AOU or cell**. Not the AOI timeseries length. Not a constant. |
| `n_dates_above_bare` | Subset of those dates where NDVI ≥ bare floor (default 0.18). Counted from **that unit’s** series only. |
| Window / AOI dates | Context only. Stamp `series_scope=window_not_aou`. **Forbidden** as `n_clear_dates` for class, persistence, or Confidence. |

`n_clear_dates = 1` on every current Najd AOU until more **unit-scoped** dates exist.

### 3.2 Persistence feature (binding)

| `n_clear_dates` | Persistence feature | `persistence_status` | What UI may say |
|-----------------|---------------------|----------------------|-----------------|
| 0 | `null` (renorm) | `no_clear` | No class |
| **1** | **`null` (renorm) or 0.0** — never ≥ 0.15 | `single_date_insufficient` | “1 clear date — temporal persistence **not** established.” AR: «تاريخ صافٍ واحد — لم يُثبت استمرار زمني.» |
| 2 | Weak only (`frac × 0.5` if `n_above < 2`) | `thin_temporal` | “Two clear dates — persistence weak / provisional.” |
| ≥ 3 | `n_above / n_clear` (clip 0–1) | `multi_date` | Persistence may vote |

**Forbidden:**

- Hardcoded `n_clear_dates=4` (or any constant).
- `n_above = min(window_dates, 3)` because the cell is green **today**.
- `feature_persistence` returning 0.5 from a single vegetated date.
- Narrating “NDVI temporal persistence” / «استمرار NDVI» when `n_clear_dates < 2`.
- Using window NDVI means as if they were that AOU’s history.

Suitability `ndvi_persistence` term: if `n_clear_dates < 2`, pass **`null` and renormalize** remaining weights. Do not inject 0.25 and call it persistence. (`engines/suitability.py` `ndvi_persistence_feature` must change.)

### 3.3 Agricultural Probability class gates (restate; now enforceable)

Already in Phase 1.3 — **binding only if `n_clear` is honest**:

1. SCL cloud/shadow/cirrus → nodata.  
2. `n_clear_dates < 3` → max `ag_class` = `possible`.  
3. `n_clear_dates < 2` (single-date) → max `ag_class` = `possible`; cannot reach `likely` or `very_likely`.  
4. Persistence feature `< 0.15` cannot reach `very_likely`.  
5. S1 / Dynamic World cannot push a class tier without optical core.

After this fix, recompute the 9 AOUs. Expected: every unit with `n_clear_dates=1` is at most `possible` (the four current `likely` drop). Probability 0–100 may stay; **class** is gated.

### 3.4 Confidence (`data_evidence`) — keep weights; fix the input

Weights unchanged (Phase-3):

| Term | Weight |
|------|--------|
| `data_quality_confidence / 100` | 0.40 |
| `n_clear_dates / 8` (cap 1) | 0.25 |
| Historical depth (0 / 0.5 / 1 for 0 / 1 / 2+ prior seasons) | 0.20 |
| Prior IoU (0 if new ID) | 0.15 |

**Input lock:** `n_clear_dates` here is the **same AOU-scoped integer**. Decision scaffolds already count `series_scope != window_not_aou` (artifacts show `n_clear_dates=1`, norm 0.125). Do not “fix” Confidence by padding to 4 or 8.

When `n_clear_dates < 2`:

- `temporal_coverage_confidence` = `(n_clear/8)*100` (12.5 if n=1).  
- Stamp `thin_temporal: true`.  
- UI: “1 clear date — temporal persistence not established.”  
- Do **not** cap the numeric Confidence to a new invented ceiling; honesty is the stamp + chip. Suitability ≠ Confidence still.

### 3.5 Stress / biotic (unchanged, confirm)

- Water/Vigor persistence term needs ≥2 of last 3 **unit** clears. Empty `stress_flags_recent` → renorm; do not invent flags from the window.  
- Biotic flag still requires ≥2 clear dates. Single-date cannot clear persistence.  
- MPI still: `<2` valid points → Insufficient; no interpolated NDMI. Mountain seeding-rec Hold unchanged.

---

## 4. Programmer must-fix (before any expansion PR)

1. **Delete** `n_clear_dates=4`, `persistence_feature=0.5` in `assign_aou_ids` (`run_ag_probability.py` ~214). Pass the **actual** unit/cell `n_clear_dates` and persistence feature.  
2. **Delete** `n_clear = len(timeseries.dates)` as the enricher input. Window length is not persistence.  
3. Count `n_clear_dates` / `n_dates_above_bare` from **that geometry’s** SCL-clear dates only.  
4. `feature_persistence`: `n_clear < 2` → 0.0 (or skip). Never 0.5 from one green date.  
5. `ndvi_persistence_feature`: `n_clear < 2` → `null` + renorm.  
6. Re-run AgProb + Decision scaffolds; rewrite AOU registry / observations / public GeoJSON. Four `likely` AOUs → `possible`.  
7. UI: `evidence_level`, evidence-basis chips, product stamp (§2). Demote “field optional” to a footnote.  
8. System field `najd_model_validation=not_validated` (or equivalent copy). Do not say the 9-AOU set is a validated Najd model.

Artifacts-first is fine. Partner UI must not keep the old `likely` stamps.

---

## 5. Platform validation program (science-owned; not a partner gate)

Required **periodically**. Never “visit every AOU.” Never a UX blocker.

Minimum paths (any **one** documented check plus this n_clear fix can move status to `system_validation_provisional` — still **not** “validated Najd model”):

1. High-resolution imagery review of a sample of AOUs (true-color QA; commercial HD if available).  
2. Known-site check (scientist-known pivots / blocks).  
3. Sparse FO sample when someone happens to visit (counts, not a census).  
4. Farmer / partner feedback log.  
5. Future government cadastral or irrigation layers.  
6. Repeat Sentinel-2 monitor runs that actually raise **AOU-scoped** `n_clear_dates`.

I sign the methodology note. Programmer does not flip `najd_model_validation` without that SHA.

Unlock to a stronger stamp is **later**. n≥20 per species×domain×horizon remains Phase-6 Learning, not this lock.

---

## 6. Forbidden (additions; previous forbidden lists still hold)

| Item | Status |
|------|--------|
| Treat window / timeseries date count as AOU `n_clear_dates` | **Forbidden** |
| Hardcoded `n_clear_dates=4` (or any constant) | **Forbidden** |
| Strong temporal persistence / `likely` / `very_likely` from one clear date | **Forbidden** |
| “9 AOUs / satellite-first = Najd model validated” | **Forbidden** |
| Field visit required to use Analysis / Decision / Seed | **Forbidden** (satellite-first stands) |
| Skip platform methodology checks because FO is optional | **Forbidden** |
| Onset MPI as post-khareef; mountain seeding recs | **Forbidden** (Hold) |
| Merge Suitability + Confidence; pest names; soil moisture % | **Forbidden** |

---

## 7. Mountain

**Unchanged.** 3.A status view may stay fail-honest. 3.B seeding-rec Hold until post-khareef MPI (`2026-09-15`–`2026-10-31`) + my Approve on that run. No experimental partner seeding toggle.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-13 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

---

## Addendum 2026-09-13 — Temporal ledger (follow-on)

**Pointer:** [`SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md`](SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md)

§3 **Live fail @ `5ad4016`** is **Historical / RESOLVED** at `85e2467` (PR #22). Do not re-open it.

**Open:** persist per-AOU dated observations (append/upsert). `n_clear` from that ledger only. `window_not_aou` stays context. Class/persistence gates in §3.2–3.3 **unchanged**.

---

## Addendum 2026-09-19 — Observation integrity pack

**Pointer:** [`SCIENCE_LOCKS_v0.4_observation_integrity.md`](SCIENCE_LOCKS_v0.4_observation_integrity.md)

Evaluator reliability / integrity pack (2026-09-19). **Go-with-fixes:** positive-area cell→AOU join; no date advance without new clear obs; alert≡timeseries counts per run_id; atomic publish. Aligns temporal ledger (merged #24). Mountain 3.B Hold unchanged.

