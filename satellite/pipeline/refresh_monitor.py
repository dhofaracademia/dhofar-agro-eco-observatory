#!/usr/bin/env python3
"""Scheduled/manual refresh. Never replace public data on a failed/stale run."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

PIPELINE = Path(__file__).resolve().parent
DEFAULT_DATA = PIPELINE.parents[1] / 'app/public/data'

def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.is_file() else {}

def scene_fingerprint(ids: list[str]) -> str:
    return hashlib.sha256('\n'.join(sorted(set(ids))).encode()).hexdigest()

def write_status(out: Path, doc: dict) -> None:
    dest = out / 'meta/monitor_status.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix('.tmp')
    temp.write_text(json.dumps(doc, indent=2) + '\n')
    temp.replace(dest)

def refresh(out: Path, *, force: bool = False, discover=None, run=None) -> int:
    from engines.observation_integrity import publish_release_with_pointer, verify_release_ids_match
    checked = datetime.now(timezone.utc).isoformat()
    previous = read_json(out / 'meta/monitor_status.json')
    status = {**previous, 'last_checked_at': checked, 'status': 'checking',
              'trigger': os.environ.get('GITHUB_EVENT_NAME', 'manual'),
              'schedule': 'daily' if os.environ.get('GITHUB_EVENT_NAME') == 'schedule' else previous.get('schedule'),
              'run_url': os.environ.get('MONITOR_RUN_URL')}
    try:
        if discover is None:
            import run_monitor as monitor
            def discover():
                interval, _ = monitor.stac_datetime_range()
                selected = monitor.pick_dates_and_items(monitor.search_items(monitor.open_catalog(), interval))
                return [monitor.pick_best_item_per_date(selected[d]).id for d in sorted(selected)]
        ids = discover()
        signature = scene_fingerprint(ids)
        status['candidate_count'] = len(ids)
        if not ids:
            status['status'] = 'no_scenes'
            write_status(out, status)
            return 0
        if not force and signature == previous.get('checked_scene_fingerprint'):
            status['status'] = 'no_new_scenes'
            write_status(out, status)
            return 0
        with tempfile.TemporaryDirectory(prefix='dhofar-refresh-') as td:
            stage = Path(td) / 'data'
            # Historical releases are immutable and unnecessary as processing input.
            shutil.copytree(out, stage, ignore=shutil.ignore_patterns('releases', 'CURRENT_LINK'))
            if run is None:
                def run(path):
                    subprocess.run([sys.executable, str(PIPELINE / 'run_monitor.py')],
                                   env={**os.environ, 'MONITOR_OUT_DATA': str(path)},
                                   check=True, timeout=5400)
            run(stage)
            manifest = read_json(stage / 'latest_release.json')
            rid = manifest.get('release_id')
            rels = manifest.get('artifacts')
            if not isinstance(rid, str) or not isinstance(rels, list) or not rels:
                raise ValueError('Missing release manifest')
            if rid == read_json(out / 'latest_release.json').get('release_id'):
                raise ValueError('Monitor did not produce a new release')
            failures = verify_release_ids_match(stage, rid, rels)
            if failures:
                raise ValueError(f'Invalid release: {failures}')
            new_meta = read_json(stage / 'meta/run_meta.json')
            old_meta = read_json(out / 'meta/run_meta.json')
            new_date = new_meta.get('observation_date') or new_meta.get('scene_capture_date')
            old_date = old_meta.get('observation_date') or old_meta.get('scene_capture_date')
            if not new_date:
                raise ValueError('Missing observation date')
            # A newly found scene can still fail cloud/coverage gates. Keep last-good.
            if old_date and (new_date < old_date or (new_date == old_date and not force)):
                status.update(status='no_new_clear_observation', checked_scene_fingerprint=signature)
                write_status(out, status)
                return 0
            alerts = read_json(stage / 'latest_alerts.geojson')
            from collections import Counter
            counts = dict(Counter(f['properties']['alert'] for f in alerts.get('features', [])))
            ts = read_json(stage / 'timeseries.json')
            row = next((r for r in ts.get('dates', []) if r.get('date') == new_date), None)
            if not counts or row is None or counts != row.get('alert_counts'):
                raise ValueError('Map and timeseries do not agree')
            publish_release_with_pointer(stage_root=stage, public_root=out,
                                         release_id=rid, relative_paths=rels)
            status.update(status='updated', last_success_at=checked, observation_date=new_date,
                          release_id=rid, checked_scene_fingerprint=signature)
        status.pop('error', None)
        write_status(out, status)
        return 0
    except Exception as exc:
        # Detailed diagnostics in workflow logs only, not in the public UI.
        print(f'Refresh failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        status.update(status='failed', error='processing_failed')
        write_status(out, status)
        return 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Reprocess unchanged scenes; never regress observation date')
    parser.add_argument('--out', type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()
    raise SystemExit(refresh(args.out.resolve(), force=args.force))
