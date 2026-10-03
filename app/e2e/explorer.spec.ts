import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const data = JSON.parse(fs.readFileSync('public/data/aou/aou_registry.geojson', 'utf8'));
const first = data.features[0];
const id = first.properties.aou_id;
const ring = first.geometry.type === 'Polygon' ? first.geometry.coordinates[0] : first.geometry.coordinates[0][0];
const [lon, lat] = ring[0];

test.beforeEach(async ({ page }) => {
  // External basemap availability must not hide data or break the core flow.
  await page.route('**/*.tile.openstreetmap.org/**', route => route.abort());
});

test('English location, coverage and saved area journey', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/en/analysis');
  await page.getByLabel('Or choose an available monitoring area').selectOption(id);
  await expect(page.getByRole('heading', { name: 'What changed?' })).toBeVisible();
  await page.getByRole('button', { name: 'Save to follow', exact: true }).click();
  await page.reload();
  await page.getByRole('button', { name: 'Monitoring area 1', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Remove saved area', exact: true })).toBeVisible();
  await page.getByLabel('Known place name or location coordinates').fill('0, 0');
  await page.getByRole('button', { name: 'Check coverage', exact: true }).click();
  await expect(page.getByText('No published agricultural monitoring unit covers this point.', { exact: false })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'What changed?' })).toHaveCount(0);
  await page.getByLabel('Known place name or location coordinates').fill(`${lat}, ${lon}`);
  await page.getByRole('button', { name: 'Check coverage', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'What changed?' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('Arabic mobile-friendly flow, invalid coordinates and specialist disclosure', async ({ page }) => {
  await page.goto('/ar/analysis');
  await expect(page.getByRole('heading', { name: 'افحص منطقة تهمك' })).toBeVisible();
  await page.getByLabel('اسم منطقة معروفة أو إحداثيات الموقع').fill('٩١،٥٣');
  await page.getByRole('button', { name: 'افحص التغطية', exact: true }).click();
  await expect(page.getByText('لم نتعرف على الموقع.', { exact: false })).toBeVisible();
  await page.getByLabel('أو اختر منطقة رصد متاحة').selectOption(id);
  await expect(page.getByRole('heading', { name: 'ما الذي تغيّر؟' })).toBeVisible();
  await page.getByText('للخبراء: الرسوم والطبقات وتفاصيل التحليل', { exact: true }).click();
  await expect(page.getByRole('tablist')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});

test('data failure is an error, never a false uncovered location', async ({ page }) => {
  await page.route('**/aou_registry.geojson', route => route.fulfill({ status: 503, body: '{}' }));
  await page.goto('/en/analysis');
  await expect(page.getByRole('alert')).toContainText('Area data could not be loaded');
  await expect(page.getByRole('button', { name: 'Check coverage', exact: true })).toHaveCount(0);
});

test('independent validation is explicitly pending and the review packet is downloadable', async ({ page }) => {
  await page.goto('/en/about');
  await expect(page.getByText('Independent review is not yet complete', { exact: true })).toBeVisible();
  await page.locator('summary').filter({ hasText: 'Download the review form' }).click();
  const link = page.getByRole('link', {name:'Download the review form',exact:true});
  const href = await link.getAttribute('href');
  const response = await page.request.get(href!);
  expect(response.ok()).toBe(true);
  expect(await response.text()).toContain('independent_of_model');
});

for (const lang of ['ar', 'en']) {
  test(`${lang}: correlated activity score is explained and never treated as land-use probability`, async ({ page }) => {
    let retained = false;
    await page.route('**/aou_registry.geojson', route => {
      const fixture = structuredClone(data);
      Object.assign(fixture.features[0].properties, {
        agricultural_probability: 12.5, ag_class: 'unlikely', alert: 'water_attention',
        assessability: 'assessable', observation_role: retained ? 'retained_last_good' : 'current_observation',
        ag_evidence: {
          version: 'activity_evidence_v2', calibrated_probability: false, score: 12.5,
          correlated_floor_collapse: true, vegetation_features_at_floor: true,
          weights: { persistence: .18, texture: .1 },
          sources: { persistence: 'derived_clear_date_counts', texture: 'default_not_measured' },
          contributions_points: { persistence: 9, texture: 3.5 },
          swir_coverage: { clear_members: 2, measured_members: 0, complete: false },
        },
      });
      return route.fulfill({ json: fixture });
    });
    await page.goto(`/${lang}/analysis`);
    const label = lang === 'ar' ? 'أو اختر منطقة رصد متاحة' : 'Or choose an available monitoring area';
    await page.getByLabel(label).selectOption(id);
    await expect(page.getByTestId('correlated-floor-warning')).toBeVisible();
    await expect(page.getByText('12.5 / 100', { exact: true })).toBeVisible();
    await page.getByText(lang === 'ar' ? 'كيف حُسبت الدرجة؟' : 'How was this score calculated?', { exact: true }).click();
    await expect(page.getByRole('cell', { name: lang === 'ar' ? 'قيمة افتراضية؛ غير مقاس' : 'Default, not measured', exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
    retained = true;
    await page.reload();
    await page.getByLabel(label).selectOption(id);
    await expect(page.getByTestId('correlated-floor-warning')).toHaveCount(0);
    await expect(page.getByText(lang === 'ar' ? 'لا توجد درجة حالية قابلة للتفسير' : 'No interpretable current score', { exact: true })).toBeVisible();
  });
}
