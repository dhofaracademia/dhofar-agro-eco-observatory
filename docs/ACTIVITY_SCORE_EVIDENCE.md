# Activity-score evidence disclosure (September 2026)

`agricultural_probability` and `ag_class` remain legacy API keys for compatibility.
They are an uncalibrated vegetation-activity heuristic and its score bands, **not**
a probability that a site is agricultural land, healthy, irrigated or independently validated.
Low greenness cannot distinguish fallow/harvested cropland from non-agricultural land.

No expert weights, discovery gates or stress thresholds change in this patch.
Current AOU scores can change because measured cell SWIR now reaches the existing
0.12-weight term rather than being dropped at the cell-to-unit boundary.
`ag_evidence.version=activity_evidence_v2` identifies this provenance-aware path.

## What is actually calculated

- `ndvi_peak` is a transform of the supplied current NDVI, not an extracted seasonal maximum.
- Phenology is a month multiplier of that same transform, not a fitted seasonal curve.
- The SWIR fallback is `0.5 * transformed_NDVI + 0.5 * transformed_NDMI`.
- Without NDRE, weights of NDVI and NDMI are 0.27 and 0.20. The four correlated
  terms carry a nominal 0.72 weight. They are not four independent observations.
- Texture defaults to 0.35 when unmeasured (3.5 points), explicitly disclosed.
- Persistence is clear-date frequency, not evidence of cultivated land use by itself.
- The floor functions are continuous clipped transforms; zeroing is not a step jump.

For September, absent NDRE, proxy SWIR and default texture:
`score = 100 * (0.4275 X + 0.26 Y + 0.18 P + 0.035)`.
If both transformed indices are zero and P=0.5, the result is 12.5.

## Provenance and measurement coverage

Every new engine result includes exact weights, feature sources, contributions in
points, raw index/count inputs, default disclosure, and `calibrated_probability=false`.
`correlated_floor_collapse` is true only when SWIR is the NDVI/NDMI proxy and both
base transforms are zero. `vegetation_features_at_floor` is separately available
when measured SWIR still contributes. Neither flag labels a site non-agricultural.

At the AOU boundary measured SWIR is accepted only when **every accepted clear
member** has a finite 0–1 feature with `b11` or `b11_b12` provenance. Zero is valid.
Use the equal-member mean, matching existing NDVI/NDMI aggregation. Partial
coverage is reported and falls back to the disclosed proxy for the whole unit.
These counts refer to cells, not a claim of full-pixel band coverage. No new
claim of statistical independence is made: NDMI and SWIR share spectral inputs.

Published registry, GeoJSON and ledger carry the same evidence object. Retained
readings retain their old evidence; the UI refuses to present it as a current
score. Old historical rows without metadata are not retrospectively fabricated.
Direct-polygon historical backfill discloses its proxy path. Do not compare
changes in scores across versions or aggregation methods as physical change.

## Limits and next scientific work

This change does not calibrate the model or establish agricultural identity.
Separate historical land-use evidence, current vegetation activity, and seasonal
anomaly detection before interpreting stress as a crop diagnosis. A low score
must not automatically suppress a moisture/vigor signal from a stressed field.
Seasonal backfill should cover an annual cycle with non-crop controls; spring
greenness alone is not ground truth. Field visits remain optional; independent
references and held-out evaluation remain pending.
