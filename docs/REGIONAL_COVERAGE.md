# Regional vegetation coverage

The regional map adds three **observatory-defined study footprints** in the Salalah plain, Jabal Qara and Najd. These are explicitly provisional operational polygons, not authoritative administrative/ecological boundaries, complete coverage of those named regions, or cadastral farmland. Their source/version is stored in `app/public/data/regions/boundaries.geojson`. Do not relabel these as official boundaries without replacing them with a licensed authoritative dataset and reprocessing all observations.

The old agricultural AOUs and their history remain independent. A regional cell is not classified as a farm; this product publishes vegetation observations, not drought, pest, crop health, water-need or restoration suitability recommendations.

## Processing

`python satellite/pipeline/refresh_regions.py` reads Sentinel-2 L2A COG assets from Microsoft Planetary Computer. Search covers each actual polygon, with a 60-day lookback and scene cloud cover below 80%. It uses the newest available date and, where available, the next date at least five days earlier. Dates can differ between regions. A recent but cloudy/partial acquisition remains visibly incomplete rather than silently presenting an older image as current.

- One fixed local Lambert azimuthal equal-area grid (center 18 N, 54 E), 60 m nearest-neighbour sampling for all bands including categorical SCL. This is a sampled regional product, **not native 10 m analysis**.
- Reflectance uses explicit STAC scale/offset when available, otherwise Sentinel processing baseline >=04.00 implies DN/10000 - 0.1; unknown baseline fails closed. Missing DN stays missing before offsets.
- Only SCL 4 (vegetation) and 5 (non-vegetated land) are admitted; water, clouds, shadows, snow and unclassified samples are excluded. Clear area therefore means **estimated clear land area**, not total satellite footprint.
- Same-date overlapping scenes fill unoccupied valid samples once, with deterministic lower-cloud-first ordering. No sample is counted twice.
- Study boundaries are densified before projection; cells are intersected in the equal-area projection and then converted to GeoJSON longitude/latitude.
- Display cells are 960 m (16 sample spacings), clipped at polygon edges. All cells remain present, including empty/unclear cells.
- A cell needs >=50 clear samples and >=50% clear sample coverage. Unknown values remain null, never zero.
- Temporal changes use common valid locations on both dates with the same thresholds. ±0.05 NDVI is a descriptive color threshold, not statistical significance or a calibrated alert.
- Clear area = projected polygon area × valid/inside sample ratio. It is an estimate; no native-pixel area precision is claimed.

## Publication and operation

`observations.json` contains all three summaries, cells, acquisition dates and source scene IDs in one atomic document. It embeds a SHA-256 hash of the exact boundary file. The browser rejects mismatched boundaries and data. A failed attempt updates only `status.json`; last-good observations are retained. Successful unchanged scenes reuse prior results, keyed by boundary hash and method version. Older-than-14-day imagery is clearly flagged in the UI.

`.github/workflows/regions.yml` runs daily at 07:47 UTC / 11:47 Oman, manually, and on relevant default-branch changes. It shares the existing publishing concurrency group to prevent data-push races. The UI refresh button only checks published results. GitHub scheduling and cloud cover do not guarantee a new daily observation.

## Validation

Synthetic regression tests exercise cloud/water exclusion, same-date overlap handling, missing-data behavior, shared-pixel comparisons, area plausibility and cell partitioning. Browser tests cover bilingual region selection, comparison, boundary-version mismatch and failed-update disclosure. These checks do not constitute independent scientific validation of land use or crop stress.

References:
- https://rasterio.readthedocs.io/en/stable/topics/virtual-warping.html
- https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a
- https://allenai.github.io/rslearn/data_sources/planetary_computer_Sentinel2/

Initial processed release: acquisition 2026-11-18, comparison 2026-11-13. Study footprints: Salalah 453.56 km²; Qara 1367.61 km²; Najd 3577.49 km². In total 6144 clipped cells. This is 5398.66 km² of operational study extent, not the area of all Dhofar or all named geographic regions. Browser CI also renders the actual published dataset and retains bilingual mobile/desktop screenshots.
