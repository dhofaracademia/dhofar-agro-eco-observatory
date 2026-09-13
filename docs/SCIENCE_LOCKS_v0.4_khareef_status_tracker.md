# Science locks — Khareef Status Tracker (Samhan → Sarfait)

> **Disclosure (EN):** Role names in these locks (“Agrofostery Scientist”, “AgriTech”, “Chief of Staff”, and others) are **AI pipeline roles** in a multi-agent engineering workflow. They are **not** an independent certified human expert, a licensed professional sign-off, or هيئة البيئة / ministry approval. **Human scientific review is still pending.** The ecological rules below stay binding for the software until a **named human reviewer** replaces this stamp.
>
> **إفصاح (AR):** أسماء الأدوار في هذه الأقفال («Agrofostery Scientist» وغيرها) هي **أدوار خط أنابيب ذكاء اصطناعي** في عمل هندسي متعدد الوكلاء. ليست خبيراً بشرياً معتمداً مستقلاً، وليست اعتماداً مهنياً مرخّصاً، وليست اعتماد هيئة البيئة أو الوزارة. **المراجعة العلمية البشرية لا تزال معلّقة.** القواعد البيئية أدناه تبقى مُلزمة للبرمجيات حتى يستبدل **مراجع بشري مسمّى** هذا الختم.


**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-13 (Asia/Muscat)  
**Status:** Binding product + honesty lock  
**Verdict: Go**  
**User mandate:** Vegetation-cover **status indicators** for the fog-escarpment mountain belt from **Jabal Samhan to Sarfait**.  
**Machine twin:** `docs/phase_khareef_status_tracker_scaffold.json`  
**Does not lift:** mountain seeding-rec Hold (3.B). This is an expansion of **3.A status**, not a plant-here product.

---

## 1. What this is

A **Khareef status tracker**: satellite indicators of greenness and canopy-moisture along the fog corridor, with a **stage** chip and data-quality honesty.

It is **not** a seeding map. It is **not** MPI persistence sold as “plant here.” It is **not** Authority-approved.

Partner copy (EN): “Khareef status — vegetation and moisture indicators. Not a seeding recommendation.”  
AR: «حالة الخريف — مؤشرات غطاء ورطوبة. ليست توصية بذر.»

---

## 2. Allowed indices (proxies)

| Index | Role | Honesty |
|-------|------|---------|
| NDVI | Greenness / cover proxy | Not biomass t/ha; not germination |
| NDMI | Canopy moisture **proxy** | **Not** soil moisture % |
| NDRE | Optional if B05 (documented B06/B07 fallback only) | If missing → `ndre=null`, `ndre_available=false` |
| True-color | Cite only | Every scene: source, date, product ID, tile, cloud % |
| MPI | Moisture **persistence** curve | Only with honest `product_kind` (below) |

SCL cloud/shadow/cirrus → nodata. **No interpolated NDMI.** Insufficient scenes → `insufficient`, not a guessed stage.

**MPI `product_kind` (binding):**

| Stamp | When |
|-------|------|
| `onset_window_dry_mpi_provisional` | T0 from onset window (current mountain product) |
| `post_khareef_mpi` | T0 in `2026-09-15`–`2026-10-31` **and** ≥1 SCL-clear S2 L2A **and** pipeline Approve on that run |
| `insufficient` | <2 valid curve points — **no class** |

**Forbidden:** labeling onset MPI as post-khareef persistence. **Forbidden:** “live Khareef onset detected” without a documented EO+calendar method in run_meta (calendar heuristic + EO assist is OK if stamped `calendar_heuristic`).

---

## 3. Spatial units — `fog_escarpment` only

**Domain:** `fog_escarpment`. **Never** mix `najd_arid` / Najd AOUs onto this tracker.

**Corridor (named segments, west ← east):**

| `segment_id` | Geography |
|--------------|-----------|
| `sarfait` | Western Qamar / Sarfait fog escarpment (Oman–Yemen frontier belt) |
| `qamar` | Jabal Qamar seaward escarpment |
| `qara` | Jabal Qara seaward escarpment (existing pilot bbox may stay) |
| `samhan` | Jabal Samhan seaward escarpment |
| `mirbat_mughsayl` | Optional coastal fog fringe already in the status map — catalog, not a fifth jabal mix |

Each segment needs a **documented WGS84 bbox** (W,S,E,N) in `run_meta.json` for the PR glance. Envelope for the belt (not a substitute for per-segment bboxes): roughly lon 53.0–55.0, lat 16.55–17.45, **seaward escarpment / monsoon woodland**. Exclude Najd leeward plateau and irrigated farms.

**Units to draw:**

- Corridor **segments** (polygons or labeled envelopes) + **status sample cells** (points/grid).  
- Status cells are **not** `recommended_sites`. If the GeoJSON path stays `recommended_sites.geojson`, collection `properties` must keep `partner_surface=status_only`, `seeding_recommendation=hold`. Prefer renaming to `khareef_status_cells.geojson` when cheap.

**Forbidden:** auto-mixing سدر/سمر/غاف onto fog cells. Fog catalog (ميست / ميتان / جميز) = **list only**.

---

## 4. Stage vocabulary (binding)

| `khareef_stage` | Meaning | Partner may show |
|-----------------|---------|------------------|
| `pre_khareef` | Before documented onset window | Yes, if dated |
| `onset` | Early-season moisture/green-up in onset window | Yes, stamped provisional |
| `peak` | Peak-season greenness | Yes **only** with clear scenes; Peak Khareef is often `insufficient` (cloud) |
| `late_khareef` | Recession still in-season | Yes |
| `post_khareef` | After T0 in the **post-khareef** window with clear evidence | **Not** until §5 gate |
| `insufficient` | Not enough SCL-clear scenes for the claimed stage | Yes (fail-honest) |

Today (2026-09-13, Asia/Muscat): preferred post window **opens 15 Sep**. Partner stage may be `late_khareef` or `insufficient` — **not** `post_khareef`.

Always show `data_quality` / `n_clear` honesty. Stage is a **label**, not a phenology model publication.

---

## 5. Partner UI — now vs after the post-khareef window

### Now (3.A tracker — **Go** to ship)

- Corridor map Samhan→Sarfait (segments + status cells).  
- NDVI / NDMI indicators + scene cite.  
- Stage chip: not `post_khareef`.  
- MPI if shown: `onset_window_dry_mpi_provisional` or `insufficient`.  
- Banner: not a seeding recommendation; seeding-rec **Hold**.  
- Fog species catalog list only.  
- Product stamp: `provisional_satellite_analytical_service`.

### After `2026-09-15`–`2026-10-31`

Allowed to **update status** to `post_khareef` / `post_khareef_mpi` **only when all** are true:

1. ≥1 SCL-clear Sentinel-2 L2A in that window on the segment.  
2. MPI run `t0_source_window=post_khareef`, `product_kind=post_khareef_mpi` or `insufficient` fail-honest.  
3. **Pipeline Approve** on that `mpi_run_meta.json` SHA.  
4. UI still **provisional**. Still **not** plant-here.

**3.B seeding-recommendation Hold is not lifted by this lock.** Tracker ≠ seeding rec. No experimental partner seeding toggle.

---

## 6. Forbidden

| Item | Status |
|------|--------|
| Plant-here / Enrichment Seeding / suitability scores as operational recs | **Forbidden** while 3.B Hold |
| Onset MPI narrated as post-khareef persistence | **Forbidden** |
| Fake live Khareef onset | **Forbidden** |
| Mixing `fog_escarpment` with `najd_arid` | **Forbidden** |
| Germination / survival % | **Forbidden** |
| Authority-approved / «معتمد من الهيئة» | **Forbidden** |
| NDMI/MPI as soil moisture % | **Forbidden** |
| Confirmed farm / official cadastral names | **Forbidden** |
| Experimental seeding toggle | **Forbidden** |
| Interpolated NDMI / invented clear dates | **Forbidden** |

---

## Mountain 3.B

**Hold unchanged.** Lift only under the existing satellite-first gate (post-khareef MPI + pipeline Approve), not because the tracker exists.

---

## Pipeline lock (AI role — not a certified human sign-off)

**Role:** Agrofostery Scientist (AI pipeline) — 2026-09-13 (Asia/Muscat)  
**Not:** independent certified human expert; not هيئة البيئة / ministry approval.  
**Human review:** pending.

**Go.** Status tracker along Samhan→Sarfait. Seeding-rec Hold stands.
