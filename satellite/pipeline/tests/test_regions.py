import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import refresh_regions as r
import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union

class RegionalTests(unittest.TestCase):
    def setUp(self):
        self.region = r.load_regions()[0]
        self.polygon, self.affine, self.inside = r.grid_for(self.region['geometry'])
    def observation(self, value, date='2026-11-20'):
        return dict(ndvi=np.full(self.inside.shape,value),ndmi=np.full(self.inside.shape,0.2),date=date,sources=[])
    def test_partition_clipped_and_no_double_counting(self):
        result=r.summarize(self.region,self.observation(0.4))
        cells=[shape(f['geometry']) for f in result['cells']]
        union=unary_union(cells)
        self.assertLess(abs(sum(c.area for c in cells)-union.area),1e-9)
        self.assertLess(union.symmetric_difference(shape(self.region['geometry'])).area,1e-6)
        self.assertEqual(sum(f['properties']['total_samples'] for f in result['cells']),result['total_samples'])
        self.assertEqual(result['clear_fraction'],1)
        self.assertGreater(result['area_km2'],100)
        self.assertLess(result['area_km2'],1000)
    def test_missing_observations_not_zero_greenness(self):
        result=r.summarize(self.region,self.observation(float('nan')))
        self.assertEqual(result['estimated_clear_area_km2'],0)
        self.assertTrue(all(f['properties']['ndvi'] is None for f in result['cells']))
    def test_comparison_uses_common_pixels(self):
        now=self.observation(0.4)
        old=self.observation(0.3,'2026-11-13')
        result=r.summarize(self.region,now,old)
        deltas=[f['properties']['ndvi_change'] for f in result['cells'] if f['properties']['ndvi_change'] is not None]
        self.assertTrue(deltas)
        self.assertTrue(all(abs(d-0.1)<1e-6 for d in deltas))
        now['ndvi'][:,::2]=np.nan
        old['ndvi'][:,1::2]=np.nan
        result=r.summarize(self.region,now,old)
        self.assertTrue(all(f['properties']['ndvi_change'] is None for f in result['cells']))
    def test_overlapping_scenes_do_not_overwrite_clear_samples(self):
        item=lambda name:SimpleNamespace(id=name, properties={'eo:cloud_cover':0}, assets={k:None for k in ('B04','B08','B11','SCL')}, datetime=SimpleNamespace(isoformat=lambda:'2026-11-20'))
        def read(it,k,*_):
            return np.full((2,2),{'B04':0.2,'B08':0.6 if it.id=='a' else 0.9,'B11':0.3,'SCL':4}[k])
        with patch.object(r,'read_band',read):
            v,m,_=r.mosaic_day([item('b'),item('a')],None,np.ones((2,2),dtype=bool))
        np.testing.assert_allclose(v,0.5)
    def test_clouds_and_water_excluded(self):
        item=SimpleNamespace(id='a',properties={},assets={k:None for k in ('B04','B08','B11','SCL')},datetime=SimpleNamespace(isoformat=lambda:'2026-11-20'))
        def read(_,k,*args):
            return np.array([[4,8],[6,3]]) if k=='SCL' else np.full((2,2),0.3)
        with patch.object(r,'read_band',read):
            v,_,_=r.mosaic_day([item],None,np.ones((2,2),dtype=bool))
        self.assertEqual(np.isfinite(v).sum(),1)
    def test_reject_shape_mismatch(self):
        obs=self.observation(0.3);obs['ndvi']=np.zeros((1,1))
        with self.assertRaises(ValueError):r.summarize(self.region,obs)
if __name__=='__main__':unittest.main()
