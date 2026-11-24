import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const raw = readFileSync(new URL('../public/data/regions/boundaries.geojson', import.meta.url), 'utf8');
const boundaries = JSON.parse(raw);
const fixture = {
  schema_version: 1, boundary_sha256: createHash('sha256').update(raw).digest('hex'), generated_at:'2026-11-23T08:00:00Z',
  regions: boundaries.features.map((f: any) => ({
    region_id:f.properties.id,date:'2026-11-20',previous_date:'2026-11-13',area_km2:300,estimated_clear_area_km2:210,clear_fraction:0.7,sources:[],
    cells:[{type:'Feature',geometry:f.geometry,properties:{id:f.properties.id,ndvi:0.4,ndmi:0.2,ndvi_change:0.1,date:'2026-11-20',previous_date:'2026-11-13',clear_fraction:0.7}}]
  }))
};
for (const locale of ['ar','en']) {
  test(`regional selection and comparison ${locale}`, async ({ page }) => {
    const errors: string[]=[];
    page.on('pageerror', e=>errors.push(e.message));
    await page.route('**/data/regions/observations.json', r=>r.fulfill({json:fixture}));
    await page.route('**/data/regions/status.json', r=>r.fulfill({json:{status:'success'}}));
    await page.goto(`/${locale}/map`);
    const section=page.getByRole('region',{name:locale==='ar'?'الرصد الإقليمي':'Regional monitoring',exact:true});
    await expect(section.getByText('2026-11-20',{exact:true})).toBeVisible();
    const select=section.getByRole('combobox').first();
    await expect(select.locator('option')).toHaveCount(3);
    await select.selectOption('qara');
    await expect(select).toHaveValue('qara');
    await section.getByRole('combobox').nth(1).selectOption('change');
    await expect(section.getByText('2026-11-13',{exact:true})).toBeVisible();
    await select.selectOption('najd');
    await expect(section.locator('.leaflet-interactive')).toHaveCount(2);
    await expect(section.locator('.leaflet-interactive').last()).not.toHaveAttribute('d', 'M0 0');
    await section.locator('.leaflet-interactive').last().click();
    await expect(section.locator('.leaflet-popup-content')).toContainText('0.1');
    await expect(section.getByText(locale==='ar'?'كم²':'km²',{exact:true})).toHaveCount(0);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
    expect(errors).toEqual([]);
  });
}
test('mismatched boundaries suppress readings',async({page})=>{
  await page.route('**/data/regions/observations.json',r=>r.fulfill({json:{...fixture,boundary_sha256:'wrong'}}));
  await page.goto('/en/map');
  const section=page.getByRole('region',{name:'Regional monitoring',exact:true});
  await expect(section.getByRole('alert')).toContainText('matching these boundaries');
  await expect(section.getByText('2026-11-20',{exact:true})).toHaveCount(0);
});
test('failed refresh retains dated published readings',async({page})=>{
  await page.route('**/data/regions/observations.json',r=>r.fulfill({json:fixture}));
  await page.route('**/data/regions/status.json',r=>r.fulfill({contentType:'text/plain; charset=utf-8',body:JSON.stringify({status:'failed'})}));
  await page.goto('/en/map');
  const section=page.getByRole('region',{name:'Regional monitoring',exact:true});
  await expect(section.getByText('2026-11-20',{exact:true})).toBeVisible();
  await expect(section.getByText(/last automatic update failed/)).toBeVisible();
});
for (const locale of ['ar', 'en']) {
  test(`published regional dataset renders ${locale}`, async ({page}, testInfo) => {
    const errors: string[]=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(`/${locale}/map`);
    const section=page.getByRole('region',{name:locale==='ar'?'الرصد الإقليمي':'Regional monitoring',exact:true});
    await expect(section.getByRole('button', {name: locale === 'ar' ? 'تحقق من التحديثات' : 'Check for updates', exact: true})).toBeEnabled();
    await expect(section.getByRole('alert')).toHaveCount(0);
    for (const id of ['salalah-plain','najd','qara']) {
      await section.getByRole('combobox').first().selectOption(id);
      await expect.poll(()=>section.locator('.leaflet-interactive').count()).toBeGreaterThan(500);
      await expect(section.locator('.leaflet-interactive').last()).not.toHaveAttribute('d','M0 0');
    }
    await section.screenshot({path:testInfo.outputPath(`regional-${locale}.png`)});
    expect(errors).toEqual([]);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
  });
}
