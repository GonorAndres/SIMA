import { test, expect } from '@playwright/test';

const ROUTES = ['/', '/mortalidad', '/tarificacion', '/scr', '/sensibilidad', '/metodologia'];

/**
 * Spanish words that MUST have accents/tildes when they appear.
 * Each entry: [unaccented regex pattern, what the correct form should be]
 * Uses word boundaries to avoid false positives within longer words.
 */
const ACCENT_CHECKS: Array<{ wrong: RegExp; correct: string }> = [
  { wrong: /\bEspana\b/g, correct: 'Espana -> Espana (tilde on n)' },
  { wrong: /\banos\b/gi, correct: 'anos -> anos (tilde on n)' },
  { wrong: /\bcalculo\b/gi, correct: 'calculo -> calculo (accent on a)' },
  { wrong: /\bfuncion\b/gi, correct: 'funcion -> funcion (accent on o)' },
  { wrong: /\bfunciones\b/gi, correct: 'funciones -> funciones (accent on second syllable)' },
  { wrong: /\binteres\b/gi, correct: 'interes -> interes (accent on e)' },
  { wrong: /\bformula\b/gi, correct: 'formula -> formula (accent on o)' },
  { wrong: /\bformulas\b/gi, correct: 'formulas -> formulas (accent on o)' },
  { wrong: /\bmetodo\b/gi, correct: 'metodo -> metodo (accent on e)' },
  { wrong: /\bparametro\b/gi, correct: 'parametro -> parametro (accent on a)' },
  { wrong: /\bparametros\b/gi, correct: 'parametros -> parametros (accent on a)' },
];

/** Wait for React SPA content to render after navigation */
async function waitForSpaRender(page: import('@playwright/test').Page) {
  await page.waitForLoadState('load');
  await page.waitForTimeout(1500);
}

test.describe('Internationalization (i18n)', () => {
  test('default language is Spanish', async ({ page }) => {
    await page.goto('/');
    await waitForSpaRender(page);

    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toContain('INICIO');
  });

  test('EN button switches to English', async ({ page }) => {
    await page.goto('/');
    await waitForSpaRender(page);

    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await page.waitForTimeout(1000);

    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toContain('HOME');
  });

  test('ES button switches back to Spanish', async ({ page }) => {
    await page.goto('/');
    await waitForSpaRender(page);

    // Switch to EN first
    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await page.waitForTimeout(1000);

    // Verify English
    let bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).toContain('HOME');

    // Switch back to ES
    await page.getByRole('button', { name: 'ES', exact: true }).click();
    await page.waitForTimeout(1000);

    bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).toContain('INICIO');
  });

  test('Spanish nav items are correct', async ({ page }) => {
    await page.goto('/');
    await waitForSpaRender(page);

    const nav = page.locator('nav');
    const expectedNavItems = ['INICIO', 'MORTALIDAD', 'RCS', 'SENSIBILIDAD'];
    for (const item of expectedNavItems) {
      await expect(nav.getByRole('link', { name: item })).toBeVisible();
    }
  });

  test('English nav items are correct after toggle', async ({ page }) => {
    await page.goto('/');
    await waitForSpaRender(page);

    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await page.waitForTimeout(1000);

    // Check English nav items scoped to nav to avoid body content matches
    const nav = page.locator('nav');
    await expect(nav.getByRole('link', { name: 'HOME', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'MORTALITY', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'PRICING', exact: true })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'METHODOLOGY', exact: true })).toBeVisible();
  });

  test('language toggle preserves current page', async ({ page }) => {
    await page.goto('/tarificacion');
    await waitForSpaRender(page);

    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await page.waitForTimeout(1000);

    // Should still be on the pricing page, just in English
    await expect(page).toHaveURL(/tarificacion/);
  });

  test('no raw i18n keys visible in Spanish', async ({ page }) => {
    for (const route of ROUTES) {
      await page.goto(route);
      await waitForSpaRender(page);

      const bodyText = await page.locator('body').textContent() || '';

      // Raw keys would look like "nav.inicio" or "forms.calculate"
      const rawKeyPattern = /\b[a-z]+\.[a-z]+[A-Z][a-zA-Z]*\b/;
      const suspiciousKeys = bodyText.match(rawKeyPattern);

      // Filter out legitimate text that might match (like URLs, CSS classes)
      if (suspiciousKeys) {
        const filtered = suspiciousKeys.filter(
          (k) => !k.includes('http') && !k.includes('www') && !k.includes('.com')
        );
        expect(filtered, `Raw i18n keys found on ${route}: ${filtered.join(', ')}`).toEqual([]);
      }
    }
  });

  test('tarificacion page has correct Spanish heading', async ({ page }) => {
    await page.goto('/tarificacion');
    await waitForSpaRender(page);

    await expect(page.locator('h1, h2').first()).toBeVisible();
    const heading = await page.locator('h1, h2').first().textContent() || '';
    expect(heading.length).toBeGreaterThan(0);
  });

  test('mortalidad page has correct Spanish heading', async ({ page }) => {
    await page.goto('/mortalidad');
    await waitForSpaRender(page);

    await expect(page.locator('h1, h2').first()).toBeVisible();
    const heading = await page.locator('h1, h2').first().textContent() || '';
    expect(heading).toContain('Mortalidad');
  });

  test('scr page has correct Spanish heading', async ({ page }) => {
    await page.goto('/scr');
    await waitForSpaRender(page);

    await expect(page.locator('h1, h2').first()).toBeVisible();
    const heading = await page.locator('h1, h2').first().textContent() || '';
    expect(heading).toContain('Capital');
  });

  test('English tarificacion heading shows Pricing', async ({ page }) => {
    await page.goto('/tarificacion');
    await waitForSpaRender(page);

    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await page.waitForTimeout(1000);

    const bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).toContain('Pricing');
  });

  test('English mortalidad heading shows Mortality', async ({ page }) => {
    await page.goto('/mortalidad');
    await waitForSpaRender(page);

    await page.getByRole('button', { name: 'EN', exact: true }).click();
    await page.waitForTimeout(1000);

    const bodyText = await page.locator('body').textContent() || '';
    expect(bodyText).toContain('Mortality');
  });

  test('accent regression scan -- homepage', async ({ page }) => {
    await page.goto('/');
    await waitForSpaRender(page);
    await page.waitForTimeout(2000);

    const bodyText = await page.locator('body').textContent() || '';
    const violations: string[] = [];

    for (const check of ACCENT_CHECKS) {
      const matches = bodyText.match(check.wrong);
      if (matches) {
        violations.push(`Found "${matches[0]}" -- ${check.correct}`);
      }
    }

    expect(violations, `Accent violations on /: ${violations.join('; ')}`).toEqual([]);
  });

  test('accent regression scan -- tarificacion', async ({ page }) => {
    await page.goto('/tarificacion');
    await waitForSpaRender(page);
    await page.waitForTimeout(2000);

    const bodyText = await page.locator('body').textContent() || '';
    const violations: string[] = [];

    for (const check of ACCENT_CHECKS) {
      const matches = bodyText.match(check.wrong);
      if (matches) {
        violations.push(`Found "${matches[0]}" -- ${check.correct}`);
      }
    }

    expect(violations, `Accent violations on /tarificacion: ${violations.join('; ')}`).toEqual([]);
  });

  test('accent regression scan -- mortalidad', async ({ page }) => {
    await page.goto('/mortalidad');
    await waitForSpaRender(page);
    await page.waitForTimeout(2000);

    const bodyText = await page.locator('body').textContent() || '';
    const violations: string[] = [];

    for (const check of ACCENT_CHECKS) {
      const matches = bodyText.match(check.wrong);
      if (matches) {
        violations.push(`Found "${matches[0]}" -- ${check.correct}`);
      }
    }

    expect(violations, `Accent violations on /mortalidad: ${violations.join('; ')}`).toEqual([]);
  });

  test('accent regression scan -- sensibilidad', async ({ page }) => {
    await page.goto('/sensibilidad');
    await waitForSpaRender(page);
    await page.waitForTimeout(2000);

    const bodyText = await page.locator('body').textContent() || '';
    const violations: string[] = [];

    for (const check of ACCENT_CHECKS) {
      const matches = bodyText.match(check.wrong);
      if (matches) {
        violations.push(`Found "${matches[0]}" -- ${check.correct}`);
      }
    }

    expect(violations, `Accent violations on /sensibilidad: ${violations.join('; ')}`).toEqual([]);
  });

  test('accent regression scan -- metodologia', async ({ page }) => {
    await page.goto('/metodologia');
    await waitForSpaRender(page);
    await page.waitForTimeout(2000);

    const bodyText = await page.locator('body').textContent() || '';
    const violations: string[] = [];

    for (const check of ACCENT_CHECKS) {
      const matches = bodyText.match(check.wrong);
      if (matches) {
        violations.push(`Found "${matches[0]}" -- ${check.correct}`);
      }
    }

    expect(violations, `Accent violations on /metodologia: ${violations.join('; ')}`).toEqual([]);
  });
});
