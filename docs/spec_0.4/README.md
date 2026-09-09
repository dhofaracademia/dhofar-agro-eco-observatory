# Spec 0.4 — Phase-1 agricultural schemas

Binding science: [`docs/SCIENCE_LOCKS_v0.4_phase1_2.md`](../SCIENCE_LOCKS_v0.4_phase1_2.md)  
Roadmap: [`docs/ROADMAP_v0.4_decision_engines.md`](../ROADMAP_v0.4_decision_engines.md)

These JSON Schemas describe **Phase-1 Agriculture** contracts only. Mountain suitability, species scores, campaign numbers, live MPI/Khareef, and pest certainty remain **out of scope / forbidden**.

## Field → SCIENCE_LOCKS mapping

| Schema file | SCIENCE_LOCKS section | Notes |
|-------------|----------------------|-------|
| `agricultural_probability.schema.json` | §1 Agricultural Probability Engine | Weights + gates; NDRE renorm when unavailable |
| `aou_identity.schema.json` | §2 AOU identity rules | `AOU-NJ-{NNNNNN}`; centroid + IoU≥0.3; never cell index |
| `aou_observation.schema.json` | §2.3 + §3 attributes@T | Separates identity from geometry/observation/probability/area @T |
| `stress_scores.schema.json` | §3 Water / Vigor Stress | 0.40 / 0.25 / 0.25 / 0.10; renorm if no history |
| `biotic_risk.schema.json` | §4 Biotic Stress Risk | `possible_biotic_stress` only — never pest name |

## NDRE (AgriTech STAC prefs)

- **Primary:** `NDRE = (B08 − B05) / (B08 + B05)` on PC Sentinel-2 L2A.
- **Documented fallback only:** if B05 missing, try B06 then B07 (record `ndre_band`).
- **No silent third formula.** If no red-edge band → omit NDRE (`ndre: null`, `ndre_available: false`) and redistribute AgProb weight 0.10 → NDVI peak + NDMI.
- SCL cloud/shadow/cirrus gates apply **before** indices.
- **SWIR:** prefer `swir_feature` from B11/B12 brightness on the STAC path; NDVI+NDMI proxy only when SWIR bands unavailable.

## Runtime artifacts (`app/public/data/`)

| Path | Role |
|------|------|
| `latest_alerts.geojson` | Monitoring grid (+ optional `aou_id`, stress, ag_probability, ndre) |
| `timeseries.json` | Window-level series (kept) |
| `meta/last_refresh.json` | Stamp |
| `aou/aou_registry.geojson` | Persistent AOU polygons + identity fields |
| `aou/aou_observations.json` | Per-AOU time series |

500 m grid remains **fallback / debug** monitoring layer; Probability Engine → segmented AOUs is the product path.

## Phases 2–6 (not built here)

See ROADMAP §35: Mountain evidence → Decision engine → Seed Intelligence → Field loop → Learning.
