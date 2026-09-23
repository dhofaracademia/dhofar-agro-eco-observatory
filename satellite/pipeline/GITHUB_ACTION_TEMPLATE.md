# Satellite readings refresh

The maintained workflow is now [monitor.yml](../../.github/workflows/monitor.yml).
See [activation instructions](../../docs/AUTOMATIC_REFRESH_AND_GUIDE.md).

Run locally with the pinned requirements installed:

```bash
python satellite/pipeline/refresh_monitor.py
```

Use `--force` to reprocess unchanged candidates without regressing the observation date.
The gallery search updates scene listings only; agricultural readings come from this pipeline.
