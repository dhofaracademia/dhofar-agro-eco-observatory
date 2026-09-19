# Science locks — Observation Integrity Pack (v0.4)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.

**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-19 (Asia/Muscat)  
**Status:** Binding honesty + pipeline integrity lock  
**Verdict: Go-with-fixes**  
**Against:** main post-#24/#25 (`68b97fb` ledger + `d3a1b6e` khareef); integrity PR stacks on that HEAD (evaluator reliability review 2026-09-19: prototype ~6/10, decision-tool ~3/10)  
**Companions:** `SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md` (PR #24), `SCIENCE_LOCKS_v0.4_evaluator_endorsement.md`  
**Machine twin:** `docs/phase_observation_integrity_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B).

**Acceptance bar (user):** a new observation must change the result; a missing observation is shown as data loss; a rerun must **not** stamp old scores with new dates.

**Merged bases (do not re-approve):**
- PR #24 @ `68b97fbc9096e2405f06462222b2817ad892447e` — Temporal Ledger (merged)  
- PR #25 @ `d3a1b6e49fa950736c6ecd71f49ad3eae2b810ff` — Khareef status (merged)  

This integrity PR stacks on that main. Hold merge for science glance.

---

## Live fails on main `1abe9ad` (binding)

1. **Cell→AOU join** uses boundary-only `poly.intersects(g)` (`engines/aou_identity.py`, `run_ag_probability.py`). Touching edges can assign cells without positive area overlap.  
2. **Alert vs timeseries counts** for the same date (`2026-09-06`) disagree on published artifacts (e.g. healthy 67 vs 65; water_attention 20 vs 26; vigor_attention 15 vs 11). One date / one run_id must not publish two classifiers.  
3. **Temporal ledger** still not on main (PR #24 open). Until merged, rescoring can wipe history / hardcode n_clear.

---

## P0 — Integrity (required before any expansion glance)

### 1. Cell → AOU join

| Rule | Binding |
|------|---------|
| Join predicate | **Positive area overlap only.** Forbidden: boundary-only `intersects` (zero-area touch). Prefer `intersection.area > 0` (or equivalent `overlaps` / buffered interior test with documented epsilon). |
| Stale IDs | **Clear** cell→AOU assignments before each reassign for that run. No leftover IDs from a prior polygon. |
| Multi-AOU cell | **One declared rule**, stamped in run_meta: either (a) assign to AOU with **max overlap area**, or (b) **area-weighted** contribution to each AOU. Silent dual-claim forbidden. |
| No overlap | Cell stays unassigned; do not invent membership from centroid alone unless run_meta stamps `join_rule=centroid_fallback` **and** that fallback is never used for n_clear / stress persistence votes. |

### 2. Observation refresh (no fake dates)

| Situation | Required behavior |
|-----------|-------------------|
| Valid new in-boundary clear cell readings for date D | Compute AOU obs from **current** member cells; upsert ledger `(aou_id, D, source)`; scores may change. |
| `rec.ndvi` / `rec.ndmi` empty **or** no valid new clear obs in-boundary | **Do not** advance `observation_date` / `last_seen_date`. **Do not** republish old NDVI/NDMI/scores under a new date. Stamp `refresh_status=stale` / `no_new_observation` and keep prior dated row. |
| Partial members cloudy | Only clear members vote; if zero clear members → treat as no new obs (row above). |

**Forbidden:** “refresh succeeded” copy when no new clear obs. **Forbidden:** copying yesterday’s scores onto today’s date.

### 3. Temporal ledger (align PR #24)

- Append/upsert by `(aou_id, date, source)`.  
- `n_clear` = distinct AOU-scoped clear ledger dates (`series_scope != window_not_aou`).  
- Window / regional series stay **context** — never ledger rows, never n_clear.  
- Empty stress / biotic history → **renorm / unknown**, **not** “no biotic issue.” Silence ≠ healthy.

Class gates unchanged: `n_clear < 2` → persistence null/0; max `ag_class=possible`.

### 4. One classifier per date / run_id

For the same `observation_date` and `run_id`, **alert layer counts** and **timeseries alert_counts** (and Decision inputs derived from them) **must match**.

| Rule | Binding |
|------|---------|
| Single pass | One classification function writes both artifacts. |
| Mismatch | Fail the publish check (non-zero) **or** stamp `consistency_status=mismatch` and block partner Decision chrome for that run — do not silently ship both. |

Live fail example to fix: `2026-09-06` alerts vs timeseries count drift on main.

---

## P1 — Ops (same PR or immediate follow; Hold merge of integrity PR until P0+P1 land)

### 5. STAC window

- Default: STAC **end date = run time** (Asia/Muscat), lookback **configurable**.  
- Fixed calendar window only when run_meta stamps `window_mode=reproducibility_fixed` + exact start/end.  
- Forbidden: silent fixed window pretending to be “live through today.”

### 6. Clear-pixel / coverage gate

- Independent **min clear-pixel count** and/or **clear coverage fraction** gate — **not** compensated by low scene cloud %.  
- Missing SCL → **block** that cell/AOU for the date **or** stamp `unclassified` — never invent clear.  
- Document thresholds in run_meta.

### 7. Atomic publish

1. Write under a temp directory / staging prefix.  
2. Consistency checks (join rule applied; alert≡timeseries counts; ledger n_clear coherent; no advanced dates without new obs).  
3. Publish as a **single `run_id`** (swap/move).  
4. AOU engine / classifier failure → **non-zero exit**; **keep last good** published set. Forbidden: half-written partner data.

---

## P2 — UX (after P0/P1 green)

### 8. Chart scope labels

Partner charts label series explicitly: **`AOU-scoped`** vs **`regional / window_not_aou`**. Never overlay without labels. Regional context cannot be captioned as “this farm’s history.”

### 9. Area honesty

Show separately when present:

| Quantity | Meaning |
|----------|---------|
| Geometry area (ha) | Polygon area |
| Cell / member area (ha) | Sum of assigned monitoring cells |
| Clear coverage % | Clear fraction of members for that date |

Do not swap labels. Do not imply cadastral farm area.

---

## Forbidden (summary)

| Item | Status |
|------|--------|
| Boundary-only intersects as membership | **Forbidden** |
| Advance observation_date without new clear in-boundary obs | **Forbidden** |
| Stamp old scores with a new date | **Forbidden** |
| Window dates as AOU n_clear / ledger | **Forbidden** |
| Empty biotic/stress history = “no problem” | **Forbidden** |
| Divergent alert vs timeseries counts for same date/run_id | **Forbidden** |
| Publish on engine failure / partial write | **Forbidden** |
| Lift mountain 3.B seeding-rec via this pack | **Forbidden** |

---

## Mountain

**3.B seeding-rec Hold unchanged.** Integrity pack applies to Najd AOU/monitor publish paths; mountain status tracker (#25) stays status-only under its own lock.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-19 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go-with-fixes.** #24 + #25 merged. This integrity PR must clear P0 (§1–4) + P1 (§5–7) before partner Decision claims “refreshed.” P2 after. Hold merge for science glance. Mountain Hold stands.
