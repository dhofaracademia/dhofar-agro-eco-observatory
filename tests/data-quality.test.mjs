import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { dataQualityConfidence as quality, MIN_VALID_PIXELS } from '../app/src/lib/dataQuality.ts';

test('missing, zero, one and sub-minimum pixel counts never yield confidence', () => {
  for (const pixel_count of [undefined, null, NaN, Infinity, -1, 0, 1, MIN_VALID_PIXELS - 1, 100.5]) assert.equal(quality({cloud_cover:0,pixel_count}),0);
  for (const cloud_cover of [undefined, null, NaN, Infinity, -1, 101]) assert.equal(quality({cloud_cover,pixel_count:2500}),0);
  assert.equal(quality({cloud_cover:0,pixel_count:2500,observation_role:'retained_last_good'}),0);
  assert.equal(quality({cloud_cover:0,pixel_count:2500,assessability:'unassessable'}),0);
});
test('score cannot exceed local observed coverage and is monotone with valid pixels', () => {
  let previous = 0;
  for (let pixels = 0; pixels <= 3000; pixels++) {
    const value = quality({cloud_cover:0,pixel_count:pixels});
    assert.ok(value <= Math.min(100,pixels / 25) + 0.05);
    assert.ok(value >= previous);previous = value;
  }
  assert.equal(quality({cloud_cover:0,pixel_count:50}),2);
  assert.equal(quality({cloud_cover:0,pixel_count:2500}),97);
});
test('Python and browser implementations agree on edge and ordinary cases', () => {
  const cases = [0,1,49,50,51,100,500,1250,2499,2500].flatMap(p => [0,0.867,10,40,100].map(c => [c,p]));
  const script = "import sys,json,runpy;f=runpy.run_path('satellite/pipeline/engines/data_quality.py')['data_quality_confidence'];print(json.dumps([f(*x) for x in json.loads(sys.argv[1])]))";
  const actual = JSON.parse(execFileSync('python', ['-c',script,JSON.stringify(cases)], {encoding:'utf8'}));
  assert.deepEqual(actual,cases.map(([cloud_cover,pixel_count])=>quality({cloud_cover,pixel_count})));
});
