# Science locks — Post-Integrity Evaluator Follow-up (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-19 (Asia/Muscat)  
**Status:** Binding honesty + pipeline integrity follow-up  
**Verdict: Go-with-fixes**  
**Against:** main HEAD `437d9203498cedda6eb43929735f503fe8ec3eff` (post-#26 integrity merge `3aaf169` + timeseries stamp align)  
**Companions:** `SCIENCE_LOCKS_v0.4_observation_integrity.md` (#26), `SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md` (#24), `SCIENCE_LOCKS_v0.4_khareef_status_tracker.md` (#25), `SCIENCE_LOCKS_v0.4_evaluator_endorsement.md`  
**Machine twin:** `docs/phase_post_integrity_evaluator_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B).

**Why this lock:** Code glance after #26 shows integrity **join / stale-date / scene coverage** paths land, but (a) scene-level clear gate alone is not AOU-honest, (b) stress/persistence still invent multi-date signal, (c) monitor still promotes public artifacts **before** AOU engine success (deferred C), (d) Khareef calendar must stay year-bound, (e) published partner data is still pre-reprocess (`last_refresh` 2026-09-13; no live `aou_observations.json` in public). UI type break is engineering — not a science lift.

**Acceptance bar (user):** partner “refreshed / integrity” claims require a successful **reprocess** under this lock; scene-clear ≠ AOU-assessable; empty stress history ≠ healthy; Nov 1 ≠ `late_khareef`.

---

## Live gaps on main `437d920` (binding)

1. **Scene-only coverage.** `run_monitor.py` gates `MIN_CLEAR_PIXELS` / `MIN_CLEAR_FRACTION` at scene/window level. No binding per-cell / per-AOU clear-coverage → `unassessable` path. A scene can pass while an AOU’s members are mostly cloudy / empty.  
2. **Invented persistence.** `run_ag_probability.py` still stamps `persistence_feature=0.5` whenever `n_clear >= 2` (registry sync / class gate), and stress calls often pass `stress_flags_recent=[]` — empty flags + fake mid persistence, not ledger-sequence stress.  
3. **Half-promote.** `run_monitor.py` atomically swaps `latest_alerts.geojson` + `timeseries.json` **then** calls `run_ag_probability`. AOU fail leaves new monitor public without AOU integrity (deferred Integrity C).  
4. **Khareef year-bound.** `calendar_stage` is mostly year-aware; still must **forbid** labeling dates after season end (e.g. **1 Nov**) as `late_khareef`. Status-only; 3.B Hold.  
5. **Published claim.** Public `meta/last_refresh.json` still `2026-09-13`; ledger artifact missing under public data. Stamp-only edits (`437d920`) ≠ reprocessed integrity.

---

## P0 — Required before any “published integrity” claim

### 1. Per-cell / per-AOU clear-coverage → `unassessable`

| Rule | Binding |
|------|---------|
| Scene gate | Scene `MIN_CLEAR_*` stays necessary — **not sufficient**. |
| Per-cell | Cell with missing SCL, SCL cloudlike, or clear-coverage below documented cell threshold → **not** a voting clear member. Stamp cell `assessability=unassessable` (or equivalent). Never invent NDVI/NDMI. |
| Per-AOU | After positive-area join, AOU clear-coverage = clear-member area (or count) / in-AOU member area (or count). If below documented **AOU min clear-coverage** (count and/or fraction in run_meta) → AOU `assessability=unassessable` for that date; **do not** advance observation_date; **do not** publish fresh stress/ag scores as “observed.” |
| Partner copy | `unassessable` ≠ healthy, ≠ “no stress,” ≠ bare. Show data-insufficient honesty. |

Document thresholds in `run_meta` (`min_clear_pixels_cell`, `min_clear_fraction_aou`, etc.).

### 2. Stress / persistence from AOU ledger sequence

| Rule | Binding |
|------|---------|
| Source | `stress_flags_recent`, persistence inputs, and any `persistence_feature` used in ag_class **must** derive from that AOU’s **ledger clear-date sequence** (SCL-clear in-boundary obs), ordered by date. |
| Empty flags | `stress_flags_recent=[]` with `n_clear >= 2` → persistence component **null / renorm** (as `engines/stress.py` already allows) — **forbidden** to treat as “no stress history = fine.” |
| Fake mid value | **Forbidden:** `persistence_feature = 0.5` solely because `n_clear >= 2`. Multi-date without a computed ledger-sequence feature → `persistence_feature=null` / 0 with `persistence_status` honest (`insufficient` / single-date rules unchanged when `n_clear < 2`). |
| Window forbid | Regional / window series still **never** feed persistence or n_clear (ledger lock stands). |

Class gates from evaluator endorsement **unchanged:** `n_clear < 2` → persistence null/0; max `ag_class=possible`.

### 3. Cross-stage atomic publish (closes Integrity deferred C)

| Rule | Binding |
|------|---------|
| Order | Build monitor + AOU outputs under **staging**. Run consistency checks (join; alert≡timeseries; ledger n_clear; no fake dates; coverage assessability). |
| Promote | **Single swap** of the public partner set **only if** AOU engine exits 0. |
| Forbidden | Promoting `latest_alerts.geojson` / `timeseries.json` to public **before** AOU success. |
| Fail | Non-zero exit; **keep last-good** public set untouched. No half-written Decision chrome. |

Intra-stage atomic writes already required by Integrity P1 §7 — this lock binds the **monitor→AOU** cross-stage gap.

### 4. Khareef calendar year-bound (status-only)

| Rule | Binding |
|------|---------|
| Year-bound | Stage windows use **asof.year** (or documented season year). Hardcoded 2026-only comparisons that mis-label other years → fix. |
| Nov 1 | **`date(Y, 11, 1)` is never `late_khareef`.** After post-window end (`Y-10-31` unless run_meta documents otherwise) → `insufficient` or next-season `pre_khareef` — not late. |
| Post stamp | `post_khareef` / `post_khareef_mpi` still only under #25 gate (clear scene in window + Approve). |
| Product | Status indicators only. **Not** plant-here. **3.B seeding-rec Hold unchanged.** |

### 5. Reprocess before claiming published integrity

| Rule | Binding |
|------|---------|
| Code ≠ data | Merging #26 / tip stamps does **not** make published partner layers integrity-honest. |
| Required | Full monitor + AOU reprocess under P0 §1–3; public `run_meta` / `last_refresh` must show new `run_id`, integrity join stamps, and ledger artifact present. |
| Claim gate | Partner / CoS / Evaluator may claim “published integrity” **only after** that reprocess succeeds and science glance on the published tip (or documented run_id) is Approve. |
| UI types | Broken UI types may Hold chrome; they do **not** waive reprocess or science rules. |

---

## P1 — Same PR or immediate follow

- Cell + AOU assessability fields plumbed to Analysis / Decision (hide or demote scores when `unassessable`).  
- Tests: (i) scene pass + AOU below coverage → unassessable / no date advance; (ii) empty stress flags ≠ healthy persistence; (iii) AOU fail after staged monitor → public last-good unchanged; (iv) asof=Nov 1 → not `late_khareef`; (v) reprocess writes ledger + matching alert/timeseries counts.

---

## Forbidden (summary)

| Item | Status |
|------|--------|
| Scene clear gate alone as AOU assessability | **Forbidden** |
| Invent clear / scores under `unassessable` | **Forbidden** |
| `persistence_feature=0.5` (or similar) from `n_clear>=2` without ledger-sequence feature | **Forbidden** |
| Empty stress flags interpreted as “no biotic / no stress problem” | **Forbidden** |
| Public monitor promote before AOU success | **Forbidden** |
| Half-publish / overwrite last-good on fail | **Forbidden** |
| `late_khareef` on/after 1 Nov (season year) | **Forbidden** |
| Claim published integrity without successful reprocess | **Forbidden** |
| Lift mountain 3.B via this follow-up | **Forbidden** |

---

## Mountain

**3.B seeding-rec Hold unchanged.** Khareef tracker remains status-only under its own lock. This follow-up does not open plant-here.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-19 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** Implement P0 §1–5 (coverage assessability, ledger-sequence stress/persistence, cross-stage atomic promote, year-bound Khareef, reprocess-before-claim). P1 tests/UX after. Mountain Hold stands. Hold partner “integrity refreshed” language until reprocess + glance Approve.
