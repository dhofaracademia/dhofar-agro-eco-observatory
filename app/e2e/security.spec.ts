import { test, expect } from '@playwright/test';
import fs from 'node:fs';

const config = JSON.parse(fs.readFileSync('../vercel.json', 'utf8'));
const securityHeaders = Object.fromEntries(config.headers[0].headers.map((h: {key: string; value: string}) => [h.key.toLowerCase(), h.value]));

test.beforeEach(async ({ page }) => {
  // Exercise the exact production policy against Vite preview in CI.
  await page.route('**/*', async route => {
    if (!route.request().isNavigationRequest()) return route.continue();
    const response = await route.fetch();
    await route.fulfill({response,headers:{...response.headers(),...securityHeaders}});
  });
});

test('public routes work with enforced CSP, while injected inline scripts are blocked', async ({page}) => {
  const errors: string[] = [];
  const policyErrors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && m.text().includes('Content Security Policy')) policyErrors.push(m.text()); });
  for (const path of ['/ar','/en/analysis','/ar/map','/en/gallery']) {
    await page.goto(path);
    await expect(page.locator('main h1')).toBeVisible();
    expect(await page.locator('header img').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  }
  expect(policyErrors).toEqual([]);
  await page.evaluate(() => {
    const script = document.createElement('script');
    script.textContent = 'window.__injectedSecurityProbe = true';
    document.body.appendChild(script);
  });
  expect(await page.evaluate(() => '__injectedSecurityProbe' in window)).toBe(false);
  expect(errors).toEqual([]);
});

test('tampered saved image metadata stays text and cannot load an attacker image', async ({page}) => {
  const unexpected: string[] = [];
  page.on('request', r => { if (r.url().includes('attacker.invalid')) unexpected.push(r.url()); });
  await page.addInitScript(() => {
    localStorage.setItem('observatory.stac.lastRefresh', JSON.stringify({updatedAt:'2026-10-03T10:00:00Z', scenes:[{
      id:'<img src=x onerror="window.__injectedSecurityProbe=true">', datetime:'2026-09-29T10:00:00Z',
      previewUrl:'https://attacker.invalid/tracker.svg', selfHref:'javascript:alert(1)',
    }]}));
  });
  await page.goto('/en/gallery');
  await expect(page.getByText('<img src=x onerror="window.__injectedSecurityProbe=true">', {exact:false})).toBeVisible();
  expect(await page.locator('img[src*="attacker.invalid"]').count()).toBe(0);
  expect(await page.evaluate(() => '__injectedSecurityProbe' in window)).toBe(false);
  expect(unexpected).toEqual([]);
});
