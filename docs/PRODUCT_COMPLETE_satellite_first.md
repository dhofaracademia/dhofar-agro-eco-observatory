# Product Complete — satellite-first (v0.4)

**Date:** 2026-09-13 (Asia/Muscat)  
**Product:** مرصد ظفار الزراعي البيئي | alias ظفار رصد | Dhofar Agro & Eco Observatory  
**Binding lock:** [`SCIENCE_LOCKS_v0.4_satellite_first.md`](SCIENCE_LOCKS_v0.4_satellite_first.md)  
**Machine twin:** [`phase_satellite_first_scaffold.json`](phase_satellite_first_scaffold.json)  
**Mandate:** The platform delivers satellite solutions **without** field visits. Field = last-resort optional additional verification only.

---

## Partner may act now (zero FO / SE)

| Surface | Status in this PR |
|---------|-------------------|
| Sentinel-2 gallery + STAC cite | Shipped (existing) |
| AgProb + AOU identity | Shipped (existing) |
| Water / vigor alerts + biotic disclaimer | Shipped (existing); FO not required |
| Analysis Decision chrome | Shipped; `no_field_visit` is an honesty chip (`caution`), **never** a red lock |
| Najd seed catalog (سدر / سمر / غاف) | Wired on Decision tab; `scientist_locked_pending_ea`; scores unvalidated |
| Timing Najd | `winter_spring_rain` \| `irrigated` |
| Field Loop | Optional last-verify copy only; SE/FO remain capture scaffolds |
| Learning | Honesty: empty Learning is **not** a readiness blocker; counts-only / experimental |

`site_field_check` / `authority_contact` apply only when an operator **logs a seeding event**. They are not gates on Analysis, Decision, or Seed catalog.

---

## Copy (AR + EN)

- Primary CTA = satellite decision / recommended action.
- Field language = «تحقق ميداني إضافي اختياري» and/or «معاينة ميدانية لاحقة اختيارية للتحقق الإضافي فقط» / “optional additional field verification (last resort)”.
- **Never** “field visit required before acting” / «يجب المعاينة الميدانية قبل الاستخدام».
- Seed vetting stays `scientist_locked_pending_ea` — never EA-approved / «معتمد من الهيئة».

---

## Mountain

### 3.A Status view — **shipped now**

- `product_kind`: `onset_window_dry_mpi_provisional` or `insufficient` (fail-honest).
- Timing: `deferred`.
- Fog catalog as a **list** (ميست / ميتان / جميز) — not plant-here cards.
- Banner: «بذر الجبل مؤجّل حتى قياس استمرار الرطوبة بعد الخريف من القمر. ليست توصية بذر.»
- No campaign numbers. No FO required. **No** experimental partner seeding toggle.

This is **not** treating all mountain partner UI as Hold. Status is allowed; **seeding recommendations** stay Hold.

### 3.B Seeding-rec Hold (unchanged)

Lift only after **all** of:

1. Preferred T0 window post-khareef `2026-09-15` … `2026-10-31` has ≥1 clear Sentinel-2 L2A (SCL).
2. `t0_source_window=post_khareef` and `product_kind=post_khareef_mpi` (or `insufficient` fail-honest).
3. Agrofostery Scientist Approve on that `mpi_run_meta` SHA.

**No post-khareef MPI re-run in this PR.** Today is 2026-09-13; the preferred window is not open.

---

## Forbidden (unchanged)

- Published germination / survival %
- Authority-approved / «معتمد من الهيئة»
- Auto weight writes / ML replacement of expert_v1
- Mixing `fog_escarpment` and `najd_arid`
- Missed FO as failure or zero
- Field visit required to use Analysis / Decision / Seed
- Onset MPI narrated as post-khareef
- Experimental partner seeding map / toggle

---

## Engine note

`satellite/pipeline/engines/evidence_gap.py`: `no_field_visit` severity `blocking` → `caution`. Honesty flag kept. Partner Decision is not red-locked.

`recommended_next_step` text is satellite-first; FO is last-resort optional, not a prerequisite.
