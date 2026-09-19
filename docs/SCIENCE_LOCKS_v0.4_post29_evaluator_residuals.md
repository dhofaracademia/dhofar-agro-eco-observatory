# Science locks — Post-#29 Evaluator Residuals (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-19 (Asia/Muscat)  
**Status:** Binding honesty — post-#29 evaluator residuals  
**Verdict: Go-with-fixes**  
**Against:** main `a85868478e5fe480e6eb5688b70486f4a982a449` (merge #29 Approve tip `f533f08f2124fbe2748139f8f4d3caf4dfa6f7cc`)  
**Companions:** `SCIENCE_LOCKS_v0.4_evaluator_round2.md`, `SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md`, `phase_evaluator_round2_case_matrix.md`  
**Machine twin:** `docs/phase_post29_evaluator_residuals_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B).

---

## Closed by #29 (do not re-open)

| Item | Status on `a858684` |
|------|--------------------------|
| Unassessable mandatory full release path (monitor→AgProb→decision) | **Landed** |
| Numeric `min_valid_area_fraction_aou` (=0.20 conservative) | **Landed** (definition of numerator still open — §R3-1) |
| New-AOU discovery `provisional_new` until n_clear≥2; no likely day-1; no mint unassessable | **Landed** |
| Round-2 cases 2–4, 6–7 regression; case 9 UX stamps | **Landed** |
| Case 10 CI workflow file | **PARTIAL** (non-blocking P2 — maintainer copy) |

Round-3 is **three honesty residuals** after those PASSes — not a rewrite of Round 2.

---

## Live residuals (binding)

### R3-1 — `valid_area_fraction` from **clear pixels inside AOU**

| Gap on main | Binding |
|-------------|---------|
| Today | `valid_area_fraction` uses ∑(`aou_overlap_area` of assessable members) / ∑(overlap of all members). `aou_overlap_area` = intersection of the **full accepted-cell polygon** with the AOU. A mostly cloudy cell that still passes the cell clear gate can overweight the AOU with opaque polygon area. |
| Required | Numerator = clear-pixel area inside the AOU (or equivalent: `aou_overlap_area × clear_fraction` / clear-pixel footprint ∩ AOU). Denominator = AOU area under consideration (member overlaps or AOU geometry — document one and stamp it). |
| Gate | `min_valid_area_fraction_aou` applies to this **clear-in-AOU** fraction — not full accepted-cell polygons. |
| Stamp | `valid_area_fraction_basis=clear_pixels_in_aou` in run_meta; keep count fraction secondary. |
| Forbid | Claiming area-honest coverage while weighting full cloudy-inclusive cell polygons. |

### R3-2 — Biotic three-state **after ledger history + re-infer**

| Gap on main | Binding |
|-------------|---------|
| Today | Three-state helper exists, but cell path passes `prior_vigor_flags=[]` and often `rules_evaluated=True` without ledger priors. AOU path ORs cell `possible_biotic_stress` without re-inferring persistence from ledger dates before T. |
| Required | After ledger history for the AOU (dates **strictly before T** + current clear members): **re-infer** biotic rules (spatial/temporal/persistence/DQ). Then assign `possible` \| `unknown` \| `not_flagged`. |
| Silence | Empty flags / no prior history → `unknown` (or `rules_evaluated=false`). **Forbidden:** `not_flagged` (or partner “no biotic issue”) from silence alone. |
| `not_flagged` | Only when `n_clear≥2`, rules **actually evaluated** with ledger-backed persistence inputs, and rules do not fire. |
| Forbid | Confirmed pest names; treating missing biotic chrome as healthy. |

### R3-3 — True all-or-nothing promote + **full rollback**

| Gap on main | Binding |
|-------------|---------|
| Today | Stage + required-file gate + file-by-file `shutil.move` into public. Mid-swap failure can leave a **mixed** public set; no restore from last-good snapshot. |
| Required | (1) Snapshot last-good public release (or write into `public_next/` then atomic rename of the release root). (2) Promote **only** after complete staged set verified. (3) On any mid-promote error: **full rollback** to last-good — partner never sees a partial new release. |
| Tests | Inject failure after N files moved → public equals pre-promote last-good. |

### R3-4 — Single staged decision run + unified `release_id`

| Gap on main | Binding |
|-------------|---------|
| Today | Decision may run under AgProb publish **and** again under monitor; `release_id` stamped after the fact. |
| Required | **One** decision scaffold invocation per partner release, against the **same** stage tree as monitor+AOU. One `release_id` (= run_id) on meta + AOU + decision artifacts **before** promote. |
| Forbid | Two decision writes with divergent ids for one public swap. |

---

## P0 — Required before next “evaluator clear”

1. **R3-1** — Clear-pixel-in-AOU `valid_area_fraction` + gate + basis stamp.  
2. **R3-2** — Ledger-backed biotic re-infer; silence ≠ `not_flagged`.  
3. **R3-3** — All-or-nothing promote with **full rollback**.  
4. **R3-4** — Single staged decision + unified `release_id`.

## P1

- Regression tests for R3-1…R3-4 + keep Round-2 suite green.  
- Case 10: land CI workflow when maintainer path allows (still non-blocking).  
- Optional: re-calibrate `min_valid_area_fraction_aou` after clear-pixel basis (may differ from 0.20 count-aligned default).

---

## Forbidden

| Item | Status |
|------|--------|
| Re-litigate closed #29 items without regression on `a858684+` | **Forbidden** |
| Full accepted-cell polygon as clear-area numerator | **Forbidden** |
| `not_flagged` / “no biotic issue” from silence or empty priors | **Forbidden** |
| Partial public promote / mixed release on failure | **Forbidden** |
| Dual decision runs / split release_ids for one promote | **Forbidden** |
| Lift mountain 3.B | **Forbidden** |

---

## Mountain

**3.B seeding-rec Hold unchanged.**

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-19 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** #29 PASSes stand. Next residual PR: clear-pixel-in-AOU area fraction; ledger biotic re-infer (silence≠not_flagged); true all-or-nothing promote with full rollback; single staged decision + one `release_id`. Hold merge of implementing PR for science glance. Mountain Hold stands.
