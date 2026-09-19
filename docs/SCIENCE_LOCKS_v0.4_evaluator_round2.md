# Science locks — Evaluator Round 2 (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-19 (Asia/Muscat)  
**Status:** Binding honesty — evaluator Round 2  
**Verdict: Go-with-fixes**  
**Against:** main `2397667b55bf84396e97140181d244a8a8b56747` (merge #28 Approve tip `147f42ba3d709ed81d0895b9fba8c57019cf799c`)  
**Note:** Evaluator synthetic cases cited against older `bd1d90c` — **re-run against this SHA** before claiming Round 2 closed.  
**Companions:** `SCIENCE_LOCKS_v0.4_evaluator_deep_recheck.md` (#28), `SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md`, `SCIENCE_LOCKS_v0.4_observation_integrity.md`  
**Machine twin:** `docs/phase_evaluator_round2_scaffold.json`  
**Case matrix:** `docs/phase_evaluator_round2_case_matrix.md` (authoritative 10 cases)  
**Does not lift:** mountain seeding-rec Hold (3.B).

---

## Closed on main `2397667` (do not re-open)

From #28 Approve — treat as **binding landed** unless regression:

| Item | Status on `2397667` |
|------|---------------------|
| Assessability pre-gate in AgProb / assign / obs write; unassessable ↛ healthy/possible | **Landed** |
| `observation_role` current vs retained_last_good | **Landed** |
| Shared `(AOU, date)` aggregate + `aggregate_id` across registry/ledger/decision | **Landed** |
| History strictly before T for priors; no self-feed | **Landed** |
| Ledger `persistence_feature` + `n_dates_above_bare` → AgProb + suitability (no `n_clear/4`) | **Landed** |
| `valid_area_fraction` computed (overlap areas); cell fraction secondary | **Landed** (gate threshold still open — §R2) |
| Biotic three-state `possible` \| `unknown` \| `not_flagged` | **Landed** |
| Atomic promote includes `decision/*` + `release_id` | **Landed** |

Round 2 is **residuals + new discovery policy**, not a rewrite of #28.

---

## Live residuals (binding)

### R2-1 — Mandatory unassessable across **all** stages

| Gap | Binding |
|-----|---------|
| Monitor classify | Partner-facing alerts must not leave the release as `healthy`/`possible` without assessability. Prefer assessability **before** monitor classify, or prove AgProb remap is always in the same release path (no public promote of pre-remap alerts). |
| Decision | Already demotes unassessable/retained — keep. Regression tests required. |
| Forbid | Any stage writing partner “current” healthy/possible when `assessability=unassessable`. |

### R2-2 — Numeric `min_valid_area_fraction_aou`

| Gap | Binding |
|-----|---------|
| Today | `valid_area_fraction` stamped; `min_valid_area_fraction_aou=null` (count gate only). |
| Required | Set a documented numeric area threshold in `run_meta` (calibrated or conservative default), and fail AOU assessability when below — not count-only forever. |
| Keep | Count fraction as secondary honesty field. |

### R2-3 — New-AOU discovery policy (**new P0**)

Cold-start / `mint_or_match_aou` can still mint IDs from assessable candidates. Round 2 binds **when a new AOU may enter the registry**.

| Rule | Binding |
|------|---------|
| Unassessable | **Never** mint or match-promote a new AOU from unassessable coverage (already skipped in cold start — keep + test). |
| Provisional | New mint stamps `discovery_status=provisional_new` (or equivalent) until `n_clear_dates >= 2` (ledger). |
| Class honesty | New AOU with `n_clear < 2`: max `ag_class=possible`; persistence null; biotic `unknown`. **Forbidden:** `likely` / `very_likely` on first clear date. |
| Geometry | Positive-area join only; min area gate (existing ha floor) stamped; no centroid-only mint for partner “current farm” claims. |
| Match vs mint | Prefer match by IoU/overlap when above threshold; mint only when no eligible prior. Stamp `match_iou` / `discovery_action=match|mint`. |
| Partner copy | Provisional new ≠ validated farm; ≠ cadastral parcel. |
| Decision | Provisional new AOUs demoted or labeled until second clear date — no action ladder as if established. |

### R2-4 — Evaluator re-base

Synthetic Round 2 cases must be re-run on **`2397667` (or later)** — not `bd1d90c`. Failures that only reproduce on pre-#28 tips are historical.

---

## P0 — Required before Round 2 “clear”

1. **R2-1** — Unassessable mandatory through monitor→AOU→decision release path (no healthy/possible current on unassessable).  
2. **R2-2** — Numeric `min_valid_area_fraction_aou` in run_meta + gate.  
3. **R2-3** — New-AOU discovery policy (provisional until n_clear≥2; no likely on day-1; no mint from unassessable; discovery stamps).  
4. **R2-4** — Re-run evaluator suite on post-#28 tip; attach SHA.

## P1

- UI/discovery: show `discovery_status` + provisional banner.  
- Tests: mint blocked when unassessable; day-1 max possible; provisional→established at n_clear=2; area threshold fails assessability; monitor/release never publishes healthy for unassessable.  
- Idempotence / shared aggregate / biotic / decision-promote **regression** suite stays green.

---

## Forbidden

| Item | Status |
|------|--------|
| Re-litigate closed #28 items without regression evidence | **Forbidden** |
| Unassessable → current healthy/possible in any partner stage | **Forbidden** |
| Count-only AOU coverage with null area gate forever | **Forbidden** (set threshold) |
| Mint new AOU from unassessable sample | **Forbidden** |
| `likely`/`very_likely` on n_clear&lt;2 new AOU | **Forbidden** |
| Evaluator “fail” claims against pre-#28 SHA as current | **Forbidden** |
| Lift mountain 3.B | **Forbidden** |

---

## Mountain

**3.B seeding-rec Hold unchanged.**

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-19 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** #28 closed deep-recheck core on `2397667`. Round 2: harden unassessable across release path, set area-fraction gate, bind **new-AOU discovery policy**, re-run evaluator on this SHA. Hold merge of implementing PR for science glance. Mountain Hold stands.
