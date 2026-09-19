# Evaluator Round 2 — authoritative 10-case matrix

**Owner:** Agrofostery Scientist (AI pipeline)  
**Date:** 2026-09-19 (Asia/Muscat)  
**Reproduce on:** main `2397667b55bf84396e97140181d244a8a8b56747` (not baseline `bd1d90c`)  
**Companions:** `SCIENCE_LOCKS_v0.4_evaluator_round2.md`, CoS Round-2 brief  
**Mountain:** 3.B Hold  

Source: evaluator synthetic full-pipeline re-check (Arabic paste) → CoS 10-case brief. Numbers below are **synthetic fixtures**, not farm observations.

| # | Pri | Case (reproduce) | Expected outcome on honest tip | Likely after #28 |
|---|-----|------------------|--------------------------------|------------------|
| 1 | P0 | **Unassessable mandatory all stages** — (a) cell `unassessable` + alert `unclear` must not become `healthy` after stress recalc; (b) AOU unassessable must not sync to `possible`/`likely` via registry; (c) empty registry + 5-pixel clear cell must **not** mint AOU with score ~88.11; (d) last-good dated ≠ stamped as current observation | One assessability gate before classify / AgProb / Decision / mint; retained_last_good never “current”; no mint from weak/unassessable sample | **Residual risk** (monitor soft path / remaps) — R2-1 |
| 2 | P0 | **Single (AOU,date) aggregate** — registry NDVI must equal ledger + decision for same unit/date; reject mixing clear+rejected (fixture: clear 0.40 vs polluted 0.65) | Shared `aggregate_id`; consumers read one blob; rejected members out of mean | **Expect PASS** (#28) — do not re-open unless FAIL |
| 3 | P0 | **Idempotent reprocess T** — same inputs ×3 → identical scores; no water-stress self-feed (fixture 33.53→45.20); history strictly `date < T`; same-day replace not append | Prior flags/persistence from before T only; reprocess replace row T | **Expect PASS** (#28) — confirm on this SHA |
| 4 | P1 | **Persistence / n_dates_above_bare** from ledger into AgProb **and** suitability; score must move when history changes (not current-only) | Ledger `persistence_feature` + `n_dates_above_bare`; no `n_clear/4` invent | **Expect PASS** (#28) |
| 5 | P0/P1 | **`valid_area_fraction`** area-based (fixture: ~2% clear area ≠ 100% / count pass); separate from `assessable_cell_fraction`; AOU fails when below **numeric** `min_valid_area_fraction_aou` | Fraction computed + **numeric gate** in run_meta | Compute **PASS**; numeric gate **residual** R2-2 |
| 6 | P1 | **Biotic three-state** after history; prior vigor/stress flags from ledger; silence ≠ healthy | `possible` \| `unknown` \| `not_flagged`; never confirmed pest | **Expect PASS** (#28) |
| 7 | P1 | **Atomic promote includes `decision/*`**; mid-copy fail → keep last-good **entire** set (no 2-release mix) | One promote set: alerts/timeseries/aou/meta/**decision** | **Expect PASS** (#28) |
| 8 | P0 | **New-AOU discovery** when registry non-empty — cold mint / match honesty | `discovery_status=provisional_new` until `n_clear≥2`; max `ag_class=possible` day-1; **no mint from unassessable**; stamp match\|mint; Decision demotes provisional | **Residual** R2-3 (policy) |
| 9 | P2 | **UX honesty** — timeseries same classifier all dates; Khareef path unify; NDMI unit vs regional; geometry area vs observed vs coverage; Decision shows insufficient/age **before** scores | Partner chrome matches stamps; no paint last-good as today healthy | Engineering — after P0 |
| 10 | P2 | **Full-pipeline regression tests** (+ CI) for cases 1–9; unit-only green ≠ merge gate | Merge gate runs synthetic pipeline cases | Residual engineering |

## Science acceptance (Round 2 clear)

Residual PR must turn **FAIL→PASS** for:

- Case **1** (full-path unassessable)  
- Case **5** numeric area gate (`min_valid_area_fraction_aou` set + enforced)  
- Case **8** discovery policy  

Cases **2–4, 6–7** must stay green (regression). Case **9–10** may ship in same or follow-on PR; not science Block if P0 clear.

## Forbidden

- Claiming FAIL on `bd1d90c` as current main failure  
- Re-litigating closed #28 items without regression evidence on `2397667+`  
- Lift mountain 3.B  

