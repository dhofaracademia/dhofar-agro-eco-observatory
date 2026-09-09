# Decision Phase-3 notes — agriculture AOU scaffolds (v0.4)

**Status:** `expert_v1_provisional` — offline artifacts only.  
**UI gate:** Analysis Decision chrome **deferred** (artifacts-first PR). **No** mountain partner decision UI.  
**Never write** to `app/public/` until science re-sign-off.

**Binding:** `docs/SCIENCE_LOCKS_v0.4_phase1_2.md` §Phase3 + AgriTech JSON field shapes.

## Scripts

| Script | Role |
|--------|------|
| `run_decision_scaffolds.py` | Read Phase-1 AOU registry/observations → decision artifacts |
| `engines/suitability.py` | `agriculture_aou` suitability + why-this-site |
| `engines/confidence.py` | `data_evidence` confidence (≠ Suitability ≠ DQ alone) |
| `engines/evidence_gap.py` | Honest missing-input list |

## Artifact paths

```
satellite/pipeline/artifacts/decision/
  aou_suitability_components.json
  aou_confidence.json
  aou_evidence_gaps.json
  action_ladder.stubs.json
  run_meta.json
```

Schemas: `docs/spec_0.4/{suitability_components,confidence,evidence_gap,action_ladder}.schema.json`.

## Locked weights

**Suitability (`agriculture_aou`):** 0.35 ag_prob · 0.20 NDVI persistence · 0.20 inverse vigor · 0.15 inverse water · 0.10 geometry stability (renorm if missing).

**Confidence (`data_evidence`):** 0.40 DQ · 0.25 n_clear/8 · 0.20 historical depth · 0.15 prior IoU.

## Hard gates

| Gate | Value |
|------|-------|
| `never_merge` | true — Suitability ≠ Confidence ≠ data_quality_confidence |
| `mountain_apply` | false — do not apply these weights to mountain cells |
| `action_auto_assign` | false — `action_ladder_suggestion` always null |
| Moisture / vigor | NDMI/NDVI stress **proxies** — not soil moisture % |
| MPI copy | If referenced: **onset-T0 provisional only** — not post-khareef for AOUs |
| Writes to `app/public/` | false |

## Inputs (read-only)

- `app/public/data/aou/aou_registry.json`
- `app/public/data/aou/aou_observations.json`

## Run

```bash
cd satellite/pipeline
python3 run_decision_scaffolds.py
```

## Done-when (artifacts PR)

1. Schemas present under `docs/spec_0.4/` for suitability / confidence / evidence_gap / action_ladder.
2. Engines + runner produce the five artifact files under `artifacts/decision/`.
3. Every suitability unit: `suitability_domain=agriculture_aou`, `status=expert_v1_provisional`, `mountain_apply=false`, `action_auto_assign=false`, `why_this_site.action_ladder_suggestion=null`.
4. Every confidence unit: `confidence_domain=data_evidence`, `not_ecological_certainty=true`, `never_merge_with_suitability=true`.
5. Evidence gaps list missing inputs honestly (NDRE, field visit, thin history, no post-khareef clear, no MPI on AOU, etc.).
6. No Analysis Decision UI chrome in this PR; no mountain UI; no writes to `app/public/` decision paths.
7. Rebased on main after Phase-2 onset-window labeling (#13).
