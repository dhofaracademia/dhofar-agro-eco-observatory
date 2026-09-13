# Science locks — Satellite-first product (no field-visit prerequisite)

> **Disclosure:** “Agrofostery Scientist”, “AgriTech Developer”, “Programmer”, and “Chief of Staff” here are **role names for AI agents** in an internal multi-agent development pipeline (engineering red-team / blue-team style), **not** sign-off by an independent certified human forestry/ecology expert. **Independent human scientific review is still pending.** These locks constrain pipeline honesty; they are not external Authority or EA approval.
>
> **إفصاح:** «Agrofostery Scientist» و«AgriTech» و«Programmer» و«Chief of Staff» هنا **أسماء أدوار لوكلاء ذكاء اصطناعي** ضمن خط تطوير متعدد الوكلاء، **وليست** مراجعة من خبير بشري مستقل معتمد في الحراجة/البيئة. **المراجعة البشرية المستقلة لا تزال معلّقة.** هذه الأقفال تضبط صدق خط الإنتاج؛ وليست اعتماداً من الهيئة أو جهة خارجية.


**Owner:** Pipeline role: Agrofostery Scientist (AI agent)  
**Audience:** Programmer + AgriTech + Chief of Staff  
**Date:** 2026-09-13 (Asia/Muscat)  
**Status:** Binding product + honesty lock  
**Mandate:** Observatory delivers **actionable satellite solutions**. Field visits are **last-resort optional extra verification**, never a prerequisite.  
**Companions:** Phase 1–6 locks, Product Spec 1.0.1  
**AI pipeline Go** (not independent human expert sign-off)

Machine-readable twin: `docs/phase_satellite_first_scaffold.json`

---

## Honesty (unchanged, still forbidden)

- Germination / survival **%** as operational truth  
- Authority-approved / «معتمد من الهيئة»  
- Auto weight writes / ML replacement of expert_v1  
- Mixing `fog_escarpment` and `najd_arid`  
- Treating missed FO as failure or as zero  
- Confirmed pest/disease/fertilizer from space  
- NDMI/MPI as soil moisture %  
- Merging Suitability + Confidence  
- Campaign ha / seed kg / crew days as official numbers  
- Calling onset-window MPI “post-khareef”

---

## 1. Copy and framing — **Go**

| Layer | Role |
|-------|------|
| Satellite + decision engines | **Primary product** |
| Analysis / Decision / Seed (Najd) | Partner may **act now** with **no** FO or SE on file |
| Field Loop (SE / FO) | **Optional last-verify** if someone later wants a ground check or a logged planting |
| Learning (LP) | Optional join when a **dated** FO exists — never a gate |

**Copy rules (AR + EN):**

- Do **not** say “يجب المعاينة الميدانية قبل الاستخدام” / “field visit required before acting.”  
- Do say the output is a **satellite attention / suitability stub**, then the **optional** line: “معاينة ميدانية لاحقة اختيارية للتحقق الإضافي فقط.”  
- Protocol steps `site_field_check` / `authority_contact` apply only when an operator **logs a seeding event**. They are **not** gates on Analysis, Decision, or Seed catalog view.  
- `possible_biotic_stress` remains “possible — satellite cannot confirm pest.” Partner may still inspect irrigation/vigor **without** filing an FO.  
- Water / vigor attention: partner may adjust irrigation / check that zone **without** an FO.

Field Loop UI, if shown at all, is a **separate optional tab**, not a blocker, not a red lock on AOU cards.

---

## 2. Complete Najd partner product **now** (no dated FO)

**Go to ship** as satellite-complete for Najd (`najd_arid` / AOU):

| Feature | Stamp that stays |
|---------|------------------|
| Sentinel-2 gallery + STAC cite | source, date, product ID, tile, cloud % |
| Agricultural Probability + AOU ids | `ag_class` + `data_quality_confidence`; AOU ≠ official farm |
| Water / Vigor scores → existing alert codes | proxy, not soil moisture %, not fertilizer diagnosis |
| Biotic risk flag | `possible_biotic_stress` + disclaimer only |
| AOU Suitability + Confidence | **separate**; `expert_v1_provisional`; no merge |
| Evidence gaps / Why-this-site | honest missing inputs; `action_ladder` manual/null |
| Seed catalog + Site×Species scaffold | 3 Najd species only; scores `unvalidated`; `scientist_locked_pending_ea` |
| Timing | `winter_spring_rain` \| `irrigated` — not Khareef |

**Not required for “complete Najd”:** any SE, FO, LP, germination window, or هيئة البيئة sign-off.

**Still not Najd-complete (do not pretend):** official farm names, campaign planner, published species suitability as truth, pest names.

---

## 3. Mountain unlock — two gates

Field visits are **not** the mountain gate. **Evidence window** is.

### 3.A Partner mountain **status** view — allowed now (fail-honest)

Partner **may** see a Restoration / mountain page that is **status-only**:

- Honest MPI product_kind: `onset_window_dry_mpi_provisional` or `insufficient`  
- Timing: `deferred`  
- Fog species **catalog** (ميست / ميتان / جميز) as a list, **not** a “plant here” card  
- Banner: “بذر الجبل مؤجّل حتى قياس استمرار الرطوبة بعد الخريف من القمر. ليست توصية بذر.”  
- No campaign numbers. No FO required.

This is **not** lifting the seeding Hold. It is completing the mountain **satellite status** product.

**Forbidden:** an `experimental` partner toggle that shows onset MPI as if it were post-khareef persistence, or that auto-assigns Terminalia to cells.

Operator-only (non-partner) artifact browser with the same banners: allowed.

### 3.B Lift **seeding-recommendation** Hold — exact gate

Hold lifts to `partner_provisional_seeding` only when **all** are true:

1. Preferred T0 window **post-khareef** (default `2026-09-15` … `2026-10-31`, Asia/Muscat) has **≥1 clear** Sentinel-2 L2A scene (SCL-gated).  
2. MPI run `t0_source_window = post_khareef` and `product_kind = post_khareef_mpi` (or `insufficient` fail-honest if <2 valid curve points). **Not** onset fallback labeled as post.  
3. Curve samples T0…T+6w, gaps = null, no interpolation.  
4. **Agrofostery Scientist re-sign-off** of that run’s `mpi_run_meta.json` (Approve on the SHA).  
5. UI still stamps MPI **provisional**; Suitability ≠ Confidence; fog species only on `fog_escarpment`; timing `late_khareef` \| `early_post_khareef` \| `deferred` if class Insufficient.  
6. Still no FO prerequisite. Still no germination %.

If post window is still empty (today is 2026-09-13; preferred window opens 15 Sep): **keep seeding Hold**. Re-run STAC; do not invent NDMI. Widen only with a written window note (≤ two weeks, still post-peak khareef), then my glance.

**`experimental` partner toggle:** **Block** for seeding recs. Status view (3.A) is the honest substitute.

---

## 4. Forbidden (confirm)

| Item | Status |
|------|--------|
| Germination / survival % as truth | Forbidden |
| Authority-approved / «معتمد من الهيئة» | Forbidden |
| Auto weight writes | Forbidden (`frozen_expert_v1`) |
| Mixing fog and Najd domains | Forbidden |
| Missed FO = failure or zero | Forbidden |
| Field visit required to use Analysis / Decision / Seed | **Forbidden** (this lock) |
| Onset MPI narrated as post-khareef | Forbidden |
| Experimental partner seeding map | Forbidden |

---

## Sign-off (AI pipeline role — not human expert credential)

**Pipeline role: Agrofostery Scientist (AI agent) — 2026-09-13 (Asia/Muscat)**  
**Go** — satellite-first Najd product; field loop optional.  
Mountain **status** view Go; mountain **seeding recs** Hold until post-khareef MPI + my SHA glance.

---

## Addendum 2026-09-13 — evidence framing (evaluator lock)

**Pointer:** [`SCIENCE_LOCKS_v0.4_evaluator_endorsement.md`](SCIENCE_LOCKS_v0.4_evaluator_endorsement.md)

Satellite-first (no FO prerequisite) **stands**. Partner chrome should lead with `evidence_level` (`satellite_only` | `enhanced_by_field_verification`) + Confidence + evidence basis + product stamp `provisional_satellite_analytical_service`. “Field optional” is a footnote, not the scientific claim. Platform methodology validation remains required; 9 single-date AOUs ≠ validated Najd model. Mountain seeding-rec Hold unchanged.
