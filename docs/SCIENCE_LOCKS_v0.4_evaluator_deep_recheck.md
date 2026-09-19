# Science locks — Evaluator Deep Re-check (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-19 (Asia/Muscat)  
**Status:** Binding honesty + evaluator deep re-check  
**Verdict: Go-with-fixes**  
**Against:** main `bd1d90c1491497efc8c6e02de87052210a498de9` (post-#27 post-integrity Approve tip `8a4a8d8`)  
**Companions:** `SCIENCE_LOCKS_v0.4_post_integrity_evaluator.md`, `SCIENCE_LOCKS_v0.4_observation_integrity.md`, `SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md`, `SCIENCE_LOCKS_v0.4_evaluator_endorsement.md`  
**Machine twin:** `docs/phase_evaluator_deep_recheck_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B).

**Why this lock:** #26/#27 closed join, stale-date, scene/cell coverage stubs, ledger persistence invent, and monitor→AOU atomic promote. Evaluator deep re-check still finds honesty holes: assessability not unified across stages; registry/ledger/decision can diverge; reprocess can self-feed date T; suitability may ignore ledger persistence; AOU clear fraction is **count-only**; biotic lacks an explicit three-state after history; decision artifacts are **outside** the promote set.

**Acceptance bar:** unassessable never reads as healthy/possible; last-good retained scores never pretend to be current observation; one (AOU, date) aggregate feeds registry + ledger + decision; reprocess of date T uses history **before** T only; area-based clear coverage; biotic never “confirmed pest”; full partner release is one atomic swap including decision.

---

## Live gaps on main `bd1d90c` (binding)

1. **Assessability after classify.** Cell path computes alert then overwrites to `unclear` when unassessable — better than silent healthy, but assessability is not a **pre-gate** for every downstream stage (Decision / suitability). Retained last-good NDVI/scores on stale/unassessable AOUs can still look like “current” without a hard `observation_role=retained_last_good` vs `current_observation` stamp.  
2. **Multi-writer aggregates.** AgProb `member_clear_means` + `build_observations` share one run; Decision (`run_decision_scaffolds.py`) re-reads registry/ledger and can recompute suitability with `ndvi_persistence=None` — not one shared (AOU, date) aggregate object.  
3. **Self-feed on T.** `_aou_scoped_clear_count` / `_persistence_feature_from_ledger` inject `pending_date` into the sequence used for the same run. Idempotent reprocess of date T must use ledger history **strictly before T** for prior features; pending may count for “including today” only when stamped as such — never double-count or feed today’s upsert into “prior” stress flags.  
4. **Suitability / AgProb wiring.** AgProb persistence from ledger largely landed (#27). Suitability still accepts `ndvi_persistence=None` and can fall back to `n_clear/4` — must take ledger `persistence_feature` + `n_dates_above_bare` (or renorm null).  
5. **Count-only clear_fraction.** `aou_assessability` uses `len(clear)/len(members)`. Lock requires `valid_area_fraction` from positive-area overlap (clear member overlap area / in-AOU member overlap area), with count as secondary.  
6. **Biotic two-ish states.** `possible_biotic_stress` bool + `unknown_insufficient_temporal_evidence` when n_clear&lt;2. After history, need explicit three-state: `possible` | `unknown` | `not_flagged` — never confirmed pest; silence ≠ healthy.  
7. **Decision outside promote.** `run_monitor.py` promote list = alerts, timeseries, aou/*, meta/* — **not** `decision/*`. Decision can lag or half-release vs AOU.  
8–10. Discovery / UI / tests = engineering; must carry honesty stamps (assessability, observation_role, biotic_status, valid_area_fraction) — not fake polish.

---

## P0 — Required before next “evaluator clear” / partner deep claim

### 1. Unified assessability before every stage

| Rule | Binding |
|------|---------|
| Pre-gate | Compute cell then AOU `assessability` **before** alert class, ag_class, Decision, suitability publish for that date. |
| Unassessable forbid | `assessability=unassessable` **never** maps to `alert=healthy`, `ag_class=possible|likely|very_likely`, or Decision “current” class. Use `unclear` / `unassessable` / demote chrome. |
| Last-good ≠ current | When scores are retained (stale / no_new / unassessable_coverage), stamp `observation_role=retained_last_good` (or equivalent) and `refresh_status` already set. Partner copy must not say “observed today.” |
| Current only | `observation_role=current_observation` only when this run’s clear in-boundary assessable sample advanced the date. |

### 2. One aggregation per (AOU, date)

| Rule | Binding |
|------|---------|
| Single aggregate | One function (or frozen struct) produces NDVI/NDMI means, stress, alerts, assessability, area fractions for `(aou_id, date)`. |
| Consumers | Registry unit, ledger row, and Decision suitability/confidence **read that aggregate** — no independent re-mean from divergent member sets. |
| Stamp | `aggregate_id` or `run_id`+`(aou_id,date)` in all three outputs. |

### 3. Idempotent reprocess — history before T only

| Rule | Binding |
|------|---------|
| Prior history | For features at date T (stress flags, persistence prior, biotic persistence), use ledger rows with `date < T` only. |
| Pending today | Including T in n_clear for “this run after upsert” is allowed **only** when documented; **forbidden** to use T’s own stress/alert as prior flag for T. |
| Re-run T | Upsert replaces row T; n_clear / persistence must match a clean replay (no double-count, no self-feed). |
| Tests | Reprocess same date twice → identical ledger row T + identical n_clear / persistence_feature. |

### 4. Persistence + n_dates_above_bare into AgProb and suitability

| Rule | Binding |
|------|---------|
| Source | `persistence_feature` and `n_dates_above_bare` from ledger sequence (post-integrity §2). |
| AgProb | Already required — keep; no invent 0.5. |
| Suitability | `compute_suitability` / Decision must pass ledger `persistence_feature` (or null renorm). **Forbidden:** `n_clear/4` as fake persistence when explicit feature null; **forbidden:** `ndvi_persistence=None` while claiming multi-date phenology. |

### 5. `valid_area_fraction` (area-based)

| Rule | Binding |
|------|---------|
| Primary | `valid_area_fraction = sum(overlap_area of assessable clear members) / sum(overlap_area of all in-AOU members)` (positive-area join overlaps). |
| Secondary | Member-count fraction may remain in meta as `clear_member_fraction`. |
| Gate | AOU unassessable when `valid_area_fraction` (and/or count gate) below run_meta thresholds. |
| Forbid | Count-only `clear_fraction` as the sole AOU coverage claim in partner meta. |

### 6. Biotic three-state after history

| `biotic_status` | When |
|-----------------|------|
| `possible` | Rules fire (possible_biotic_stress true) — still **not** pest certainty. |
| `unknown` | History insufficient **or** rules inconclusive after history (incl. n_clear&lt;2 → unknown; empty flags ≠ healthy). |
| `not_flagged` | n_clear≥2 and rules explicitly do not fire — **not** “no biotic issue forever,” stamp as satellite non-flag only. |

**Forbidden:** confirmed pest/disease names; treating missing flag as healthy; dropping unknown after history.

### 7. Full-release atomic publish (incl. Decision)

| Rule | Binding |
|------|---------|
| Stage | Monitor + AOU + Decision scaffolds write under one stage / run_id. |
| Promote | Single swap includes `decision/*` (suitability, confidence, evidence_gaps, decision run_meta) **with** alerts/timeseries/aou/meta. |
| Fail | Non-zero anywhere in the release chain → keep last-good **entire** public set (incl. decision). |
| Extends | Post-integrity §3 (monitor→AOU) to **full partner release**. |

---

## P1 — Engineering with honesty stamps (8–10)

8. **Discovery / APIs** — expose assessability, observation_role, valid_area_fraction, biotic_status, aggregate/run_id.  
9. **UI** — demote or banner unassessable / retained_last_good; never paint last-good as today’s healthy.  
10. **Tests** — unassessable↛healthy; shared aggregate equality registry=ledger=decision; reprocess idempotence; area fraction vs count divergence fixture; biotic three-state; promote includes decision or fails closed.

---

## Forbidden (summary)

| Item | Status |
|------|--------|
| Unassessable → healthy / possible / likely | **Forbidden** |
| Retained last-good presented as current obs | **Forbidden** |
| Divergent (AOU,date) aggregates across registry/ledger/decision | **Forbidden** |
| Self-feed of date T into prior stress/persistence for T | **Forbidden** |
| Suitability fake persistence (`n_clear/4` / null while claiming multi-date) | **Forbidden** |
| Count-only clear_fraction as sole AOU coverage | **Forbidden** |
| Confirmed pest; silence = healthy | **Forbidden** |
| Public decision lag / half-release vs AOU | **Forbidden** |
| Lift mountain 3.B | **Forbidden** |

---

## Mountain

**3.B seeding-rec Hold unchanged.** This re-check is Najd integrity / Decision honesty only.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-19 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** Implement P0 §1–7; P1 §8–10 with honesty stamps. Hold merge of the implementing PR for science glance. Mountain Hold stands.
