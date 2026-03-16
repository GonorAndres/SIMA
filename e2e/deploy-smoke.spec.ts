import { test, expect } from '@playwright/test';

const ROUTES = [
  { path: '/', name: 'Homepage' },
  { path: '/mortalidad', name: 'Mortalidad' },
  { path: '/tarificacion', name: 'Tarificacion' },
  { path: '/scr', name: 'SCR' },
  { path: '/sensibilidad', name: 'Sensibilidad' },
  { path: '/metodologia', name: 'Metodologia' },
];

test.describe('Deploy Smoke Tests', () => {
  for (const route of ROUTES) {
    test(`${route.name} page returns HTTP 200`, async ({ page }) => {
      const response = await page.goto(route.path);
      expect(response?.status()).toBe(200);
    });
  }

  test('all navigation links are visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const nav = page.locator('nav');
    const navTexts = ['INICIO', 'MORTALIDAD', 'RCS', 'SENSIBILIDAD'];
    for (const text of navTexts) {
      await expect(nav.getByRole('link', { name: text })).toBeVisible();
    }
  });

  test('no console errors on homepage', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    expect(errors).toEqual([]);
  });

  test('no console errors on tarificacion', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/tarificacion');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    expect(errors).toEqual([]);
  });

  test('footer contains SIMA branding', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const footer = page.locator('footer');
    await expect(footer).toContainText('SIMA');
  });

  test('footer contains data source attribution', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const footer = page.locator('footer');
    await expect(footer).toContainText('INEGI/CONAPO');
  });

  test('homepage stat cards are present', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');
    await page.waitForTimeout(3000);

    const body = await page.locator('body').textContent();
    expect(body).toContain('77');
  });

  test('DEMO button is present on homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    await expect(page.getByRole('button', { name: /demo/i })).toBeVisible();
  });

  test('no broken images on homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');
    await page.waitForTimeout(2000);

    const brokenImages = await page.evaluate(() => {
      const images = document.querySelectorAll('img');
      const broken: string[] = [];
      images.forEach((img) => {
        if (img.naturalWidth === 0 && img.src) {
          broken.push(img.src);
        }
      });
      return broken;
    });

    expect(brokenImages).toEqual([]);
  });

  test('no horizontal scroll on any page', async ({ page }) => {
    for (const route of ROUTES) {
      await page.goto(route.path);
      await page.waitForLoadState('load');

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });

      expect(hasHorizontalScroll, `Horizontal scroll detected on ${route.path}`).toBe(false);
    }
  });

  test('language toggle buttons are visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('load');

    const esButton = page.getByRole('button', { name: 'ES', exact: true });
    const enButton = page.getByRole('button', { name: 'EN', exact: true });

    const esVisible = await esButton.isVisible().catch(() => false);
    const enVisible = await enButton.isVisible().catch(() => false);

    expect(esVisible || enVisible).toBe(true);
  });
});
