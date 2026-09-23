# Automatic readings and the public guide

## What ships

- `.github/workflows/monitor.yml`: daily discovery at 05:17 UTC / 09:17 Oman, plus authenticated **Run workflow** in GitHub Actions. Scheduled executions can be delayed by GitHub.
- `refresh_monitor.py`: checks candidate scene IDs, skips unchanged candidates, processes in an isolated directory, validates release IDs and map/time-series counts, and retains the previous release on failure or a regressing observation date.
- `meta/monitor_status.json`: last attempted check, its outcome, and the last successful publication. This is separate from the observation date and is written by actual runs only.
- Immutable release folders and a session-pinned frontend manifest. A new release prompts the visitor to reload rather than mixing charts and map versions.
- English/Arabic Start Here guide, explanations and suggested follow-up, separate dates, contextual help, keyboard focus and same-page language switching. Heavy routes load on demand.

## Activation

Merge the reviewed PR into the default branch. GitHub Actions must be enabled and allowed to write repository contents. If branch rules prohibit bot writes, configure an authorised data-publication PR path; do not bypass branch protection. The GitHub credential used to install workflows needs workflow-write permission.

Run **Satellite readings refresh → Run workflow** once to verify the full STAC path. Leave `force` off for ordinary updates; turn it on only to reprocess unchanged scenes with updated code. First execution may process the current candidates because no previous check fingerprint exists.

Keep the existing GitHub-to-Vercel integration enabled for default-branch data commits. Verify that the commit produces a deployment and that the served release ID matches; a successful GitHub run is not proof that Vercel deployed it.

No public browser receives a token. The administrator link opens GitHub's authenticated workflow page; it is not a public processing endpoint.

## Honest behaviour

Daily checking does not guarantee daily usable satellite images. Clouds and coverage gates still apply. The imagery page's search button refreshes the scene catalogue only. The public "Check for published updates" button does not start a compute job.

Before the first real run the UI says that update status is unavailable; it does not claim the scheduler has run. Restoration/mountain products retain their own publication path and are not silently updated by this agricultural workflow.

## Validation

Run `python satellite/pipeline/tests/run_all.py` with the pinned requirements installed, then `cd app && npm ci && npm run build`. New offline tests cover successful complete publication, unchanged scenes, processing failure, date regression, inconsistent counts and refusal to overwrite a release.

A real cloud-processing run and production deployment require the workflow to be installed and run. Local synthetic tests do not validate new scientific observations. Previously identified historical backfill calibration/alignment work is separate from this delivery.
