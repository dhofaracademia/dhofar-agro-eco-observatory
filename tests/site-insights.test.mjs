import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseCoordinates, containsPoint, comparison } from '../app/src/lib/siteInsights.ts';

test('coordinates accept Arabic digits and reject ambiguous or invalid input', () => {
  assert.deepEqual(parseCoordinates('١٨٫٠٠٠، ٥٣٫٩٠٠'), [18, 53.9]);
  assert.deepEqual(parseCoordinates('18.00, 53.90'), [18, 53.9]);
  for (const input of ['', '18,', '91,53', '18,181', '18,53,7', 'latitude 18 longitude 53']) assert.equal(parseCoordinates(input), null);
});
const ring = [[0,0],[10,0],[10,10],[0,10],[0,0]];
const hole = [[3,3],[7,3],[7,7],[3,7],[3,3]];
test('coverage is polygon containment, excludes holes and distant locations', () => {
  const geometry = { type: 'Polygon', coordinates: [ring, hole] };
  assert.equal(containsPoint(geometry, 2, 2), true);
  assert.equal(containsPoint(geometry, 5, 5), false);
  assert.equal(containsPoint(geometry, 11, 2), false);
  assert.equal(containsPoint(geometry, 0, 0), true);
  assert.equal(containsPoint({ type: 'MultiPolygon', coordinates: [[ring]] }, 2, 2), true);
});
const row = (date, ndvi, extra = {}) => ({date, ndvi, ndmi:0.1, series_scope:'aou_members_aggregate', tile:'39QYA', assessability:'assessable', observation_role:'current_observation', valid_area_fraction:0.9, ...extra});
test('comparison uses distinct dates, same unit method and valid data; never regional context', () => {
  const r = comparison([row('2026-09-01',0.5),row('2026-09-09',0.7)]);
  assert.equal(r.reason,null);assert.ok(Math.abs(r.ndvi - 0.2) < 1e-10);
  assert.equal(comparison([row('2026-09-09',0.5),row('2026-09-09',0.7)]).reason,'history');
  assert.equal(comparison([row('2026-09-01',0.5,{series_scope:'aou_direct'}),row('2026-09-09',0.7)]).reason,'method');
  assert.equal(comparison([row('2026-09-01',0.5),row('2026-09-09',0.7,{series_scope:'window_not_aou'})]).reason,'method');
  assert.equal(comparison([row('2026-09-01',0.5,{tile:'other'}),row('2026-09-09',0.7)]).reason,'method');
});
test('retained, cloudy, missing and unassessable latest data cannot suggest current change', () => {
  for (const extra of [{observation_role:'retained_last_good'},{assessability:'unassessable'},{valid_area_fraction:0.05},{ndvi:null}]) {
    assert.equal(comparison([row('2026-09-01',0.5),row('2026-09-09',0.7,extra)]).reason,'quality');
  }
  assert.equal(comparison([]).reason,'quality');
});
