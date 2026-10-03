"""Regressions for correlated floors and cell → AOU → ledger provenance."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.ag_probability import agricultural_probability, measured_swir_for_members
from run_ag_probability import assign_aou_ids, build_observations, enrich_features
from test_observation_integrity import _cell
from shapely.geometry import box, mapping


class ActivityEvidenceTests(unittest.TestCase):
    def score(self, **extra):
        return agricultural_probability(ndvi=0.1651, ndmi=-0.0554,
            n_clear_dates=8, n_dates_above_bare=4, month=9, **extra)

    def test_actual_floor_is_12_5_and_not_four_independent_measurements(self):
        result = self.score()
        e = result['ag_evidence']
        self.assertEqual(result['agricultural_probability'], 12.5)
        self.assertTrue(e['correlated_floor_collapse'])
        self.assertEqual(e['correlated_ndvi_ndmi_weight'], .72)
        self.assertEqual(e['sources']['texture'], 'default_not_measured')
        self.assertEqual(e['contributions_points']['persistence'], 9)
        self.assertEqual(e['contributions_points']['texture'], 3.5)
        self.assertAlmostEqual(sum(e['contributions_points'].values()), e['score'])
        self.assertFalse(e['calibrated_probability'])

    def test_measured_swir_zero_is_valid_and_invalid_values_are_missing(self):
        for value in [0, .6]:
            e = self.score(swir_feature=value)['ag_evidence']
            self.assertEqual(e['sources']['swir'], 'band_derived_swir')
            self.assertFalse(e['correlated_floor_collapse'])
            self.assertAlmostEqual(e['score'], 12.5 + 12 * value)
        for value in [float('nan'), float('inf'), -1, True, '0.6']:
            self.assertTrue(self.score(swir_feature=value)['ag_evidence']['correlated_floor_collapse'])

    def test_partial_or_proxy_coverage_cannot_be_called_measured(self):
        good = {'swir_feature': .4, 'swir_source': 'b11'}
        for other in [{}, {'swir_feature': .9, 'swir_source': 'proxy_ndvi_ndmi'}]:
            value, meta = measured_swir_for_members([good, other])
            self.assertIsNone(value)
            self.assertEqual(meta['measured_members'], 1)
            self.assertFalse(meta['complete'])
        value, meta = measured_swir_for_members([good, {'swir_feature': 0, 'swir_source': 'b11_b12'}])
        self.assertEqual(value, .2)
        self.assertTrue(meta['complete'])

    def test_grid_enrichment_never_promotes_an_unverified_number_to_measurement(self):
        for source in [None, 'proxy_ndvi_ndmi', 'b11']:
            cell = _cell(0,0,1,1,ndvi=.1651,ndmi=-.0554,date='2026-09-26')
            cell['properties']['swir_feature'] = .6
            if source is not None:
                cell['properties']['swir_source'] = source
            props = enrich_features([cell], month=9)[0]['properties']
            expected = 'band_derived_swir' if source == 'b11' else 'derived_ndvi_ndmi'
            self.assertEqual(props['ag_evidence']['sources']['swir'], expected)
            self.assertEqual(props['swir_source'], 'b11' if source == 'b11' else 'proxy_ndvi_ndmi')

    def test_provenance_survives_unit_registry_and_ledger_and_retained_reading(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'registry.json'
            reg = {'type':'aou_registry', 'version':'0.4.1', 'units':[{
                'aou_id':'AOU-NJ-000001', 'active':True,
                'geometry':mapping(box(0,0,1,1)), 'centroid_lon':.5,'centroid_lat':.5,
                'area_ha_est':5., 'first_seen_date':'2026-08-01', 'last_seen_date':'2026-08-01',
            }]}
            path.write_text(json.dumps(reg))
            cell = _cell(0,0,1,1,ndvi=.1651,ndmi=-.0554,date='2026-09-26')
            cell['properties'].update(swir_feature=.6,swir_source='b11', water_stress_score=60, vigor_stress_score=30)
            cells, registry, features, _ = assign_aou_ids([cell],path,'2026-09-26')
            e = features[0]['properties']['ag_evidence']
            self.assertEqual(e['sources']['swir'], 'band_derived_swir')
            self.assertEqual(e['swir_coverage']['measured_members'], 1)
            self.assertEqual(e, registry['units'][0]['ag_evidence'])
            self.assertEqual(e, features[0]['properties']['aou_date_aggregate']['ag_evidence'])
            ledger = build_observations(features,{'dates':[]},cells,existing_path=None)
            self.assertEqual(e, ledger['units'][0]['observations'][-1]['ag_evidence'])
            path.write_text(json.dumps(registry))
            cloudy = copy.deepcopy(cell)
            cloudy['properties'].update(pixel_count=0,valid_pixel_count=0,clear_fraction=0,date='2026-09-27')
            _, _, retained, _ = assign_aou_ids([cloudy],path,'2026-09-27',ledger=ledger)
            self.assertNotEqual(retained[0]['properties']['observation_role'], 'current_observation')
            self.assertEqual(retained[0]['properties']['ag_evidence'], e)

if __name__ == '__main__':
    unittest.main()
