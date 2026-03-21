// @ts-check
import { test, expect } from '@playwright/test';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Collect console errors and failed network requests during a page load. */
async function collectPageIssues(page) {
  const consoleErrors = [];
  const failedRequests = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(err.message));
  page.on('requestfailed', (req) => {
    const url = req.url();
    const isSameOrigin = url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost');
    if (isSameOrigin) {
      failedRequests.push(`${req.failure()?.errorText} — ${url}`);
    }
  });
  page.on('response', (res) => {
    // Flag 4xx/5xx responses on same-origin requests only
    // (CDN tiles and external fonts may fail in offline/CI environments)
    const url = res.url();
    const isSameOrigin = url.startsWith('http://127.0.0.1') || url.startsWith('http://localhost');
    if (res.status() >= 400 && isSameOrigin && !url.includes('favicon')) {
      failedRequests.push(`HTTP ${res.status()} — ${url}`);
    }
  });

  return { consoleErrors, failedRequests };
}

// ── Homepage ──────────────────────────────────────────────────────────────────

test.describe('Homepage', () => {
  test('loads without console errors', async ({ page }) => {
    const { consoleErrors } = await collectPageIssues(page);
    await page.goto('/');
    // Give async JS (waitForLibs + fetch) time to settle
    await page.waitForTimeout(3000);
    expect(
      consoleErrors,
      `Console errors found:\n${consoleErrors.join('\n')}`
    ).toHaveLength(0);
  });

  test('has no failed or 4xx/5xx network requests', async ({ page }) => {
    const { failedRequests } = await collectPageIssues(page);
    await page.goto('/');
    await page.waitForTimeout(3000);
    expect(
      failedRequests,
      `Failed requests:\n${failedRequests.join('\n')}`
    ).toHaveLength(0);
  });

  test('/data/regions.json returns 200 with valid JSON', async ({ page }) => {
    const response = await page.request.get('/data/regions.json');
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('regions');
    expect(Array.isArray(body.regions)).toBe(true);
    expect(body.regions.length).toBeGreaterThanOrEqual(17);
  });

  test('map element is present', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#map')).toBeVisible();
  });

  test('Leaflet map initializes (container rendered)', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 12000 });
  });

  test('region sidebar populates with region cards', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.region-card').first()).toBeVisible({ timeout: 10000 });
    const count = await page.locator('.region-card').count();
    expect(count).toBeGreaterThanOrEqual(17);
  });

  test('i18n _t object is injected', async ({ page }) => {
    await page.goto('/');
    const hasT = await page.evaluate(() => typeof _t !== 'undefined' && typeof _t.popupType === 'string');
    expect(hasT).toBe(true);
  });

  test('_base variable resolves data URLs without 404', async ({ page }) => {
    await page.goto('/');
    const base = await page.evaluate(() => typeof _base !== 'undefined' ? _base : null);
    expect(base).not.toBeNull();
    // Verify the resolved URL for regions.json actually returns 200
    const response = await page.request.get(`${base}/data/regions.json`);
    expect(response.status()).toBe(200);
  });

  test('clicking a region card loads zone data', async ({ page }) => {
    await page.goto('/');
    await page.locator('.region-card').first().waitFor({ timeout: 10000 });
    await page.locator('.region-card').first().click();
    // dataInfo should become non-empty after zone loads
    await expect(page.locator('#dataInfo')).not.toBeEmpty({ timeout: 8000 });
  });
});

// ── Data files ────────────────────────────────────────────────────────────────

test.describe('Zone data files', () => {
  const ZONES = [
    'Gulf_of_Mexico', 'Great_Lakes', 'East_Coast_US', 'West_Coast_US',
    'Mediterranean', 'North_Sea', 'English_Channel',
  ];

  for (const zone of ZONES) {
    test(`/data/${zone}.json returns 200 with valid structure`, async ({ page }) => {
      const response = await page.request.get(`/data/${zone}.json`);
      expect(response.status(), `${zone}.json returned ${response.status()}`).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty('zone');
      expect(body).toHaveProperty('transports');
      expect(Array.isArray(body.transports)).toBe(true);
    });
  }
});

// ── About page ────────────────────────────────────────────────────────────────

test.describe('About page', () => {
  test('loads without console errors', async ({ page }) => {
    const { consoleErrors } = await collectPageIssues(page);
    await page.goto('/about/');
    await page.waitForTimeout(1000);
    expect(
      consoleErrors,
      `Console errors found:\n${consoleErrors.join('\n')}`
    ).toHaveLength(0);
  });

  test('has no failed network requests', async ({ page }) => {
    const { failedRequests } = await collectPageIssues(page);
    await page.goto('/about/');
    await page.waitForTimeout(1000);
    expect(
      failedRequests,
      `Failed requests:\n${failedRequests.join('\n')}`
    ).toHaveLength(0);
  });

  test('has H1 and meaningful content', async ({ page }) => {
    await page.goto('/about/');
    await expect(page.locator('h1')).toBeVisible();
    const h1 = await page.locator('h1').textContent();
    expect(h1?.length).toBeGreaterThan(3);
  });
});

// ── Multilingual pages ────────────────────────────────────────────────────────

test.describe('Multilingual pages', () => {
  for (const lang of ['es', 'fr']) {
    test(`/${lang}/ loads without console errors`, async ({ page }) => {
      const { consoleErrors } = await collectPageIssues(page);
      await page.goto(`/${lang}/`);
      await page.waitForTimeout(3000);
      expect(
        consoleErrors,
        `Console errors on /${lang}/:\n${consoleErrors.join('\n')}`
      ).toHaveLength(0);
    });

    test(`/${lang}/ has no failed network requests`, async ({ page }) => {
      const { failedRequests } = await collectPageIssues(page);
      await page.goto(`/${lang}/`);
      await page.waitForTimeout(3000);
      expect(
        failedRequests,
        `Failed requests on /${lang}/:\n${failedRequests.join('\n')}`
      ).toHaveLength(0);
    });

    test(`/${lang}/ has correct lang attribute`, async ({ page }) => {
      await page.goto(`/${lang}/`);
      const htmlLang = await page.locator('html').getAttribute('lang');
      expect(htmlLang).toBe(lang);
    });
  }
});
