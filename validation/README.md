# Independent reference pilot — pending, not validated

This workflow is outside `satellite/pipeline`. It does not call the model, copy model outputs into reference labels, or treat CI success as evidence of scientific accuracy.

The first packet freezes all nine published monitoring units from one release. It is a small, selected pilot, not a representative test set. It checks **agricultural land use only**, not the correctness of irrigation/stress/pest or mountain-seeding advice. Add independent negative sites, seasons and holdout areas before estimating broader accuracy.

## Reviewer workflow

1. Give the independent reviewer only `app/public/validation/pilot-20260924/cases.geojson` and `reviews.csv`, not `validation/pilot-20260924/predictions.json`. The public repository is accessible, so blinding is procedural, not an access-control guarantee. Reviewers must avoid consulting predictions before recording judgments.
2. Inspect external evidence appropriate to the area/date: independently interpreted imagery from another sensor, a documented field observation, or a dated external land-use record. Recalculating the same Sentinel NDVI or checking the pipeline against its own output is **not** an independent reference. A field visit is optional, not a condition for using the site.
3. Enter `yes`, `no`, or `uncertain` in `agricultural_presence`. Complete reviewer name/identifier, `reference_kind` (`independent_sensor`, `field_observation`, `external_record`), date, a retrievable HTTPS evidence reference, `independent_of_model=yes`, and notes explaining observation-date compatibility and judgment. Do not fill labels from model predictions. Leave unresolved cases uncertain.
4. Preserve the original file and evidence; record who collected/reviewed them and any disagreement. An independent person must inspect the supplied evidence and temporal/geographic correspondence. The script checks schema/declarations; it cannot authenticate reviewers, prove independence, or verify URLs or judgments.
5. After labels are fixed, compare with the frozen baseline:

```sh
python validation/review.py score \
  --baseline validation/pilot-20260924/predictions.json \
  --reviews completed-reviews.csv --out review-report.json
```

The evaluator rejects duplicate/unknown cases and release mismatches. It reports counts, abstentions, uncertain references and descriptive sample agreement. With no labels, agreement is null. Even a perfect pilot does not mark the model validated or authorize recommendations. Reference uncertainty, selection bias, independent negative examples and diagnostic targets need separate evaluation.

No independent judgments have been collected in this change. P1 remains open until real evidence has been supplied and reviewed. Do not add synthetic test labels to the public packet.

## Coverage-confidence correction

`app/src/data/qualityPolicy.json` is shared by Python and the browser. The existing processing gate is 50 valid pixels (2% of a nominal 2,500-pixel cell); this is an engineering minimum, not an empirically calibrated accuracy threshold. Missing/invalid cloud coverage or fewer than 50 valid pixels produces an insufficient-quality score of zero. Scene clarity can no longer inflate the score above the percentage of locally observed pixels. A 50-pixel cell is capped at 2/100 and maps to unclear, rather than a healthy/stress label. UI explains insufficient evidence instead of displaying a positive confidence percentage.

The score remains a provisional image-quality heuristic, not a probability of a correct diagnosis. Quality flags and model accuracy must remain separate. Existing high-coverage readings may be unchanged after reprocessing; that is expected.
