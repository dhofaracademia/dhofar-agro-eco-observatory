# Science locks — Post-#30 Evaluator Follow-up (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-20 (Asia/Muscat)  
**Status:** Binding honesty — post-#30 evaluator follow-up  
**Verdict: Go-with-fixes**  
**Against:** main `059f7e70b5e7cfea491804f5db4afd894b6f439f` (merge #30 Approve tip `549736d17f58d4d6071e528db799e727822baf0e`)  
**Companions:** `SCIENCE_LOCKS_v0.4_post29_evaluator_residuals.md`, `SCIENCE_LOCKS_v0.4_evaluator_round2.md`  
**Machine twin:** `docs/phase_post30_evaluator_followup_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B).

---

## Closed by #30 (do not re-open)

| Item | Status on `059f7e7` |
|------|--------------------------|
| R3-1 clear-pixel-weighted numerator (`overlap × clear_fraction` when present) | **Landed** |
| R3-2 biotic three-state + ledger priors; silence → unknown (not not_flagged) | **Landed** (current-vs-retained split still open — §R4-2) |
| R3-3 atomic promote with last-good snapshot + rollback | **Landed** (release *pointer* semantics still open — §R4-3) |
| R3-4 single staged decision run under monitor | **Landed** (artifact-wide `release_id` still open — §R4-4) |

Round-4 is **four honesty tightenings** after those PASSes — not a rewrite of #29/#30.

---

## Live residuals (binding)

### R4-1 — Coverage: clear pixels + **full AOU target** denominator; no silent full-clear

| Gap on main | Binding |
|-------------|---------|
| Today | `aou_target_area` exists but production callers omit it → denom = ∑(member overlaps), not full AOU geometry. Missing `clear_fraction` → assessable member contributes **full** overlap (silent full-clear). |
| Required numerator | Clear-pixel area in AOU only. Missing `clear_fraction` → **do not** invent 1.0; exclude from clear numerator (or mark coverage incomplete / unassessable). Stamp `clear_fraction_missing=true` when any member lacks it. |
| Required denominator | **Full AOU target area** (geometry area, or documented AOU area_ha→m²). Always pass `aou_target_area` from registry geometry. Member-overlap sum may remain a diagnostic only. |
| Stamp | `valid_area_fraction_basis=clear_pixels_in_aou`; `valid_area_fraction_denominator=aou_target_area`. |
| Forbid | Silent full-clear when `clear_fraction` absent; partner “~100% clear” from polygon-only math. |

### R4-2 — Biotic: current infer only when **new + assessable**; rejected → current unknown; last-trusted separate

| Gap on main | Binding |
|-------------|---------|
| Today | Re-infer can run whenever `clear_members` + `n_clear≥2`, including paths where `observation_role` is retained / coverage unassessable. One `biotic_status` field mixes current and retained. |
| Current biotic | Infer / publish as **current** only when `has_new` **and** `assessability=assessable` **and** rules evaluated with ledger priors. Otherwise current = `unknown` (or omitted), never `not_flagged` from silence. |
| Rejected / unassessable date | Current biotic = `unknown`; do not carry forward a fresh infer as “today’s” class. |
| Last-trusted | Retain prior biotic under `biotic_status_last_trusted` + dated `observation_role=retained_last_good` (or equivalent). Partner chrome must not paint retained as current. |
| Forbid | Confirmed pest; retained biotic presented as current observation. |

### R4-3 — True **release pointer** / all-or-nothing publish semantics

| Gap on main | Binding |
|-------------|---------|
| Today | Promote mutates a live `OUT_DATA` tree file-by-file (with rollback). No immutable release directory + single pointer partners read. |
| Required | Each successful publish writes a complete release under `releases/<release_id>/` (or equivalent). Partner “current” is a **single pointer** (`CURRENT` → that id, or `latest_release.json` naming the id). Swap pointer **only after** the full release tree is verified. |
| Rollback | On failure: pointer unchanged; partial `releases/<id>/` discarded or never pointed. File-level rollback of a mutable live tree is insufficient alone. |
| Forbid | Mid-publish mixed live tree as the only publish model; pointer advance before full tree OK. |

### R4-4 — Single `release_id` on **all** monitor / AOU / decision artifacts

| Gap on main | Binding |
|-------------|---------|
| Today | `release_id` stamped on meta + decision `run_meta`; AOU registry/observations and alerts/timeseries are not required to carry the same id. |
| Required | One `release_id` (= run_id) on: `meta/*`, `decision/*`, `aou/*` (registry + observations), `latest_alerts`, `timeseries` (properties or sibling meta). Readable in every partner-facing artifact for that publish. |
| Verify | Pre-promote check: all required artifacts share identical `release_id` or promote aborts. |
| Forbid | Split ids across stages of one public swap. |

---

## P0 — Required before next “evaluator clear”

1. **R4-1** — Full AOU denom + no silent full-clear on missing `clear_fraction`.  
2. **R4-2** — Current biotic only when new+assessable; rejected → unknown; last-trusted separate.  
3. **R4-3** — Immutable release tree + single CURRENT pointer (all-or-nothing semantics).  
4. **R4-4** — Same `release_id` on monitor + AOU + decision artifacts; pre-promote equality gate.

## P1

- Regression tests for R4-1…R4-4; keep #29/#30 suites green.  
- UI: show retained biotic / coverage-incomplete banners.  
- Optional: migrate live tree readers to pointer-only.

---

## Forbidden

| Item | Status |
|------|--------|
| Re-litigate closed #30 R3 items without regression on `059f7e7+` | **Forbidden** |
| Invent clear_fraction=1.0 when missing | **Forbidden** |
| Denom = member overlaps only while claiming AOU-area honesty | **Forbidden** |
| Current biotic infer on retained / unassessable path | **Forbidden** |
| Advance CURRENT pointer before full release verified | **Forbidden** |
| Split release_ids in one publish | **Forbidden** |
| Lift mountain 3.B | **Forbidden** |

---

## Mountain

**3.B seeding-rec Hold unchanged.**

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-20 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** #30 PASSes stand. Next residual PR: AOU-target denom + honest missing clear_fraction; current-vs-last-trusted biotic; release pointer publish; artifact-wide `release_id`. Hold merge of implementing PR for science glance. Mountain Hold stands.
