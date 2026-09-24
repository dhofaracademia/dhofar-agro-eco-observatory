"""Offline integration tests for refresh publication, failure and no-op paths."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refresh_monitor import refresh, scene_fingerprint
from engines.observation_integrity import publish_release_with_pointer

class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'public'
        self.out.mkdir()
        self.seed(self.out, 'old', '2026-09-06')

    def seed(self, path, rid, date):
        docs = {
            'meta/run_meta.json': {'observation_date': date},
            'latest_alerts.geojson': {'features': [{'properties': {'alert': 'healthy'}}]},
            'timeseries.json': {'dates': [{'date': date, 'alert_counts': {'healthy': 1}}]},
        }
        for rel, doc in docs.items():
            p = path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({**doc, 'release_id': rid}))
        (path / 'latest_release.json').write_text(json.dumps({'release_id': rid, 'artifacts': list(docs)}))
        return list(docs)

    def status(self):
        return json.loads((self.out / 'meta/monitor_status.json').read_text())

    def test_new_accepted_scene_publishes_complete_release(self):
        rc = refresh(self.out, discover=lambda: ['new-scene'], run=lambda p: self.seed(p, 'new', '2026-09-10'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.status()['status'], 'updated')
        self.assertEqual((self.out / 'CURRENT').read_text().strip(), 'new')
        self.assertTrue((self.out / 'releases/new/timeseries.json').is_file())

    def test_unchanged_candidates_skip_processing(self):
        p = self.out / 'meta/monitor_status.json'
        p.write_text(json.dumps({'checked_scene_fingerprint': scene_fingerprint(['a', 'b'])}))
        def must_not_run(_):
            raise AssertionError('unnecessary processing')
        self.assertEqual(refresh(self.out, discover=lambda: ['b', 'a'], run=must_not_run), 0)
        self.assertEqual(self.status()['status'], 'no_new_scenes')

    def test_failure_keeps_last_good(self):
        before = (self.out / 'latest_alerts.geojson').read_bytes()
        def fail(path):
            (path / 'latest_alerts.geojson').write_text('broken')
            raise RuntimeError('synthetic failure')
        self.assertEqual(refresh(self.out, discover=lambda: ['new'], run=fail), 1)
        self.assertEqual((self.out / 'latest_alerts.geojson').read_bytes(), before)
        self.assertEqual(self.status()['status'], 'failed')

    def test_force_does_not_regress_observation_date(self):
        self.assertEqual(refresh(self.out, force=True, discover=lambda: ['old-scene'],
            run=lambda p: self.seed(p, 'new', '2026-09-01')), 0)
        self.assertEqual(self.status()['status'], 'no_new_clear_observation')
        self.assertFalse((self.out / 'releases/new').exists())

    def test_mismatched_counts_never_publish(self):
        def bad(path):
            self.seed(path, 'new', '2026-09-10')
            (path / 'timeseries.json').write_text(json.dumps({'release_id': 'new', 'dates': []}))
        self.assertEqual(refresh(self.out, discover=lambda: ['new'], run=bad), 1)
        self.assertFalse((self.out / 'releases/new').exists())

    def test_successful_empty_check_clears_previous_error_and_records_attempt(self):
        p = self.out / 'meta/monitor_status.json'
        p.write_text(json.dumps({'status': 'failed', 'error': 'previous_failure'}))
        self.assertEqual(refresh(self.out, discover=lambda: []), 0)
        self.assertEqual(self.status()['status'], 'no_scenes')
        self.assertNotIn('error', self.status())
        self.assertIn('last_attempt_at', self.status())

    def test_existing_release_is_never_replaced(self):
        stage = Path(self.temp.name) / 'stage'
        stage.mkdir()
        rels = self.seed(stage, 'fixed', '2026-09-06')
        publish_release_with_pointer(stage_root=stage, public_root=self.out, release_id='fixed', relative_paths=rels)
        old = (self.out / 'releases/fixed/latest_alerts.geojson').read_bytes()
        self.seed(stage, 'fixed', '2026-09-10')
        with self.assertRaises(FileExistsError):
            publish_release_with_pointer(stage_root=stage, public_root=self.out, release_id='fixed', relative_paths=rels, fail_mid_copy=1)
        self.assertEqual((self.out / 'releases/fixed/latest_alerts.geojson').read_bytes(), old)
        self.assertTrue((self.out / 'releases/fixed/timeseries.json').exists())

if __name__ == '__main__':
    unittest.main()
