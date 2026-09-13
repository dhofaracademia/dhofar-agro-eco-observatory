# Product honesty — Evidence level + single-obs (v0.4)

**Date:** 2026-09-13 (Asia/Muscat)  
**Product:** مرصد ظفار الزراعي البيئي | alias ظفار رصد | Dhofar Agro & Eco Observatory  
**Binding lock:** [`SCIENCE_LOCKS_v0.4_evaluator_endorsement.md`](SCIENCE_LOCKS_v0.4_evaluator_endorsement.md)  
**Companion:** [`SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md`](SCIENCE_LOCKS_v0.4_aou_temporal_ledger.md) (ledger append/upsert; `n_clear` from ledger)  
**Machine twin:** [`phase_evaluator_endorsement_scaffold.json`](phase_evaluator_endorsement_scaffold.json)

## Stakeholder optional FO ≠ platform scientific validation

| Layer | Meaning |
|-------|---------|
| Partner FO | Optional per AOU. Upgrades `evidence_level` to `enhanced_by_field_verification`. **Never** a gate on Analysis / Decision / Seed. |
| Platform validation | Methodology checks owned by Agrofostery Scientist. Independent of whether any partner filed an FO. |

**Today:** `najd_model_validation = not_validated`.  
**Product stamp:** `provisional_satellite_analytical_service` / «خدمة تحليلية مؤقتة من القمر الصناعي».  
**Forbidden:** “9 AOUs / satellite-first = Najd model scientifically validated.”

## Single clear obs ≠ multi-date persistence

- `n_clear_dates` = distinct dates in the AOU observation ledger (`aou_observations.json`), never window length (today **1** on all 9 Najd AOUs: `2026-09-06`).
- Ledger **append/upserts** by `(aou_id, date)` — does not wipe to latest-only.
- Window / `timeseries.json` length is **context only** (`series_scope=window_not_aou`).
- Persistence feature is **null / 0.0** when `n_clear < 2` — never 0.25 or 0.5 from one green date.
- `ag_class` capped at `possible` when `n_clear < 2` (and `< 3`).
- UI chip: «رصد صافٍ واحد ≠ استمرار متعدد التواريخ» / “1 clear obs ≠ multi-date persistence”.

## Mountain

Seeding-rec Hold unchanged (post-khareef MPI `2026-09-15`–`2026-10-31` + scientist SHA).
