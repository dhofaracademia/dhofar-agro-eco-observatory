# Evaluator CI workflow (Case 10 / post-#30)

GitHub OAuth used by this agent **lacks `workflow` scope**, so
`.github/workflows/evaluator-tests.yml` cannot be pushed from this tip.

**Maintainer action:** copy `satellite/pipeline/EVALUATOR_TESTS_GITHUB_ACTION.yml`
to `.github/workflows/evaluator-tests.yml` with a token/app that has workflow
write (or via the GitHub UI). Required skip ≠ green — suites must actually run.

Pinned deps: `satellite/pipeline/requirements.txt`.
Synthetic fixtures only in PR CI (no live Sentinel-2).

Local merge-gate:

```bash
cd satellite/pipeline
python tests/test_observation_integrity.py
python tests/test_post_integrity_evaluator.py
python tests/test_evaluator_deep_recheck.py
python tests/test_evaluator_round2.py
python tests/test_post29_residuals.py
python tests/test_post30_followup.py
cd ../../app && npm ci && npm run build
```
