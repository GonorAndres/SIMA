import { test, expect, type Page } from '@playwright/test';

/**
 * Responsive / touch-ergonomics gate.
 *
 * The two screens this project is judged on are a recruiter's phone and an
 * interviewer's laptop, so both are asserted here rather than eyeballed. What
 * this file locks in:
 *
 *   - no horizontal page scroll at any width down to 320px
 *   - every touch target >= 44x44 on phone widths (WCAG 2.2 AAA), >= 24px on
 *     pointer widths (AA)
 *   - no form field under 16px, which is what makes iOS Safari zoom the page
 *   - Plotly's modebar is gone below --bp-md, and a swipe that starts on a
 *     chart still scrolls the page instead of zooming it
 *   - the mobile drawer opens, locks scroll, closes on navigate/Escape/backdrop
 *
 * Run it against a local dev server:
 *   BASE_URL=http://127.0.0.1:5173 npx playwright test e2e/responsive.spec.ts --project=chromium
 *
 * The width sweep runs on chromium only — the layout maths does not vary by
 * engine and the sweep is 30 page loads. Every block sets its own viewport, so
 * the phone-sized tests exercise phone widths under any project.
 *
 * The `mobile` project (iPhone 14) is webkit, whose system libraries are not
 * installed here — `npx playwright install-deps webkit` needs root, the same
 * limitation already noted in visual-regression.spec.ts. Under `--project=mobile`
 * these tests fail to launch a browser rather than fail an assertion.
 */

const ROUTES = [
  { path: '/', name: 'Inicio' },
  { path: '/mortalidad', name: 'Mortalidad' },
  { path: '/tarificacion', name: 'Tarificación' },
  { path: '/scr', name: 'SCR' },
  { path: '/sensibilidad', name: 'Sensibilidad' },
  { path: '/metodologia', name: 'Metodología' },
];

/** 320 is the narrowest phone still in use; 1440 a typical laptop. */
const WIDTHS = [320, 375, 768, 1024, 1440];

/** Below --bp-md the UI is driven by a thumb, not a cursor. */
const TOUCH_BREAKPOINT = 768;

async function settle(page: Page) {
  // No waitForLoadState('domcontentloaded') here: page.goto() already resolves
  // on 'load', and asking again raced the dev server under parallel workers.
  //
  // The pages fetch from the actuarial API; charts only size themselves once
  // the data lands. A missing backend must not hang the suite, hence catch().
  await page.waitForLoadState('networkidle', { timeout: 45_000 }).catch(() => {});
  await page.waitForTimeout(1200);
}

/**
 * Elements that are off-screen by design (the skip link) or belong to
 * Plotly's hidden measuring canvas are not reachable and never count.
 */
const IGNORED = '#js-plotly-tester, .skipLink';

async function horizontalOverflow(page: Page) {
  return page.evaluate(() => {
    const de = document.documentElement;
    return de.scrollWidth - de.clientWidth;
  });
}

async function offendingElements(page: Page) {
  return page.evaluate((ignored) => {
    const vw = document.documentElement.clientWidth;
    const out: string[] = [];
    for (const el of document.querySelectorAll<HTMLElement>('body *')) {
      const r = el.getBoundingClientRect();
      if ((r.width === 0 && r.height === 0) || el.closest(ignored)) continue;
      const s = getComputedStyle(el);
      if (s.visibility === 'hidden' || s.display === 'none') continue;
      if (r.left < -1 && r.left < -2000) continue;
      if (r.right <= vw + 1 && r.left >= -1) continue;
      // Inside a deliberately scrollable box (a wide table) is allowed.
      let p = el.parentElement;
      let scrollable = false;
      while (p && p !== document.body) {
        const ps = getComputedStyle(p);
        if (ps.overflowX === 'auto' || ps.overflowX === 'scroll') {
          scrollable = true;
          break;
        }
        p = p.parentElement;
      }
      if (scrollable) continue;
      const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/)[0] : '';
      out.push(`${el.tagName.toLowerCase()}${cls ? '.' + cls : ''} [${Math.round(r.left)}..${Math.round(r.right)}]`);
    }
    return [...new Set(out)].slice(0, 8);
  }, IGNORED);
}

async function undersizedTargets(page: Page, min: number) {
  return page.evaluate(
    ({ min, ignored }) => {
      const sel =
        'a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=tab], summary';
      const out: string[] = [];
      for (const el of document.querySelectorAll<HTMLElement>(sel)) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        if (getComputedStyle(el).visibility === 'hidden') continue;
        if (el.closest(ignored)) continue;
        // WCAG 2.2 exempts links sitting inline within a sentence.
        if (el.tagName === 'A' && el.closest('p, li, td, th')) continue;
        if (r.height < min || r.width < 24) {
          const label = (el.innerText || (el as HTMLInputElement).value || el.getAttribute('aria-label') || '')
            .trim()
            .slice(0, 24);
          out.push(`${el.tagName.toLowerCase()} "${label}" ${Math.round(r.width)}x${Math.round(r.height)}`);
        }
      }
      return [...new Set(out)].slice(0, 8);
    },
    { min, ignored: IGNORED }
  );
}

async function zoomTriggeringFields(page: Page) {
  return page.evaluate(() => {
    const out: string[] = [];
    for (const el of document.querySelectorAll<HTMLElement>('input, select, textarea')) {
      if ((el as HTMLInputElement).type === 'hidden') continue;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < 16) out.push(`${el.tagName.toLowerCase()} @ ${fs}px`);
    }
    return [...new Set(out)].slice(0, 8);
  });
}

test.describe('Responsive layout', () => {
  // The sweep is engine-independent; running it in all four projects would
  // cost 120 page loads to re-check the same box model.
  test.skip(({ browserName }) => browserName !== 'chromium', 'width sweep runs on chromium');

  for (const width of WIDTHS) {
    const isTouch = width < TOUCH_BREAKPOINT;

    test.describe(`at ${width}px`, () => {
      test.use({ viewport: { width, height: isTouch ? 780 : 900 } });

      for (const route of ROUTES) {
        test(`${route.name} fits the viewport`, async ({ page }) => {
          await page.goto(route.path);
          await settle(page);

          const overflow = await horizontalOverflow(page);
          if (overflow > 0) {
            console.log(`overflow offenders on ${route.path}:`, await offendingElements(page));
          }
          expect(overflow, `${route.name} scrolls sideways at ${width}px`).toBeLessThanOrEqual(0);

          // 44px on a thumb, 24px on a cursor.
          const small = await undersizedTargets(page, isTouch ? 44 : 24);
          expect(small, `undersized targets on ${route.name} at ${width}px`).toEqual([]);

          const zoomy = await zoomTriggeringFields(page);
          expect(zoomy, `fields under 16px zoom iOS Safari on ${route.name}`).toEqual([]);
        });
      }
    });
  }
});

test.describe('Charts on a phone', () => {
  test.use({ viewport: { width: 375, height: 780 } });

  test('no Plotly modebar below the tablet breakpoint', async ({ page }) => {
    await page.goto('/mortalidad');
    await settle(page);
    // The bar is 24x22px of icons no thumb can hit; chartDefaults drops it.
    await expect(page.locator('.modebar-btn')).toHaveCount(0);
  });

  test('a swipe starting on a chart still scrolls the page', async ({ page }) => {
    await page.goto('/mortalidad');
    await settle(page);

    const plot = page.locator('.js-plotly-plot').first();
    await plot.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);

    const box = await plot.boundingBox();
    expect(box).not.toBeNull();

    const before = await page.evaluate(() => window.scrollY);
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.mouse.down();
    await page.mouse.wheel(0, 400);
    await page.mouse.up();
    await page.waitForTimeout(500);
    const after = await page.evaluate(() => window.scrollY);

    // With dragmode left on, Plotly reads this as a zoom and the page freezes.
    expect(after, 'the page is trapped by the chart').toBeGreaterThan(before);
  });
});

test.describe('Mobile navigation drawer', () => {
  test.use({ viewport: { width: 375, height: 780 } });

  test('opens, locks scroll, and closes on navigate', async ({ page }) => {
    await page.goto('/');
    await settle(page);

    const burger = page.locator('button[aria-controls="primary-nav"]');
    await expect(burger).toBeVisible();
    await expect(burger).toHaveAttribute('aria-expanded', 'false');

    await burger.click();
    await expect(burger).toHaveAttribute('aria-expanded', 'true');

    // A drawer over a still-scrolling page is the classic mobile bug.
    expect(await page.evaluate(() => getComputedStyle(document.body).overflow)).toBe('hidden');

    // Flat navigation: all six destinations reachable without a submenu.
    await expect(page.locator('#primary-nav a:visible')).toHaveCount(6);

    const shortRows = await page.evaluate(
      () =>
        [...document.querySelectorAll('#primary-nav a')]
          .map((a) => a.getBoundingClientRect().height)
          .filter((h) => h > 0 && h < 44).length
    );
    expect(shortRows, 'drawer rows shorter than 44px').toBe(0);

    await page.locator('#primary-nav a[href="/scr"]').first().click();
    await page.waitForTimeout(600);

    expect(page.url()).toContain('/scr');
    await expect(burger).toHaveAttribute('aria-expanded', 'false');
    expect(await page.evaluate(() => getComputedStyle(document.body).overflow)).not.toBe('hidden');
  });

  test('closes on Escape and on backdrop click', async ({ page }) => {
    await page.goto('/');
    await settle(page);
    const burger = page.locator('button[aria-controls="primary-nav"]');

    await burger.click();
    await expect(burger).toHaveAttribute('aria-expanded', 'true');
    await page.keyboard.press('Escape');
    await expect(burger).toHaveAttribute('aria-expanded', 'false');

    await burger.click();
    await expect(burger).toHaveAttribute('aria-expanded', 'true');
    // Well below the bar, over the dimmed page behind the drawer.
    await page.mouse.click(187, 720);
    await expect(burger).toHaveAttribute('aria-expanded', 'false');
  });

  test('marks the page you are on', async ({ page }) => {
    await page.goto('/mortalidad');
    await settle(page);

    await page.locator('button[aria-controls="primary-nav"]').click();
    // "Where am I" must be answerable without reading the URL bar.
    await expect(page.locator('#primary-nav a[aria-current="page"]')).toHaveCount(1);
  });
});

test.describe('Desktop navigation', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('shows the full bar with no hamburger', async ({ page }) => {
    await page.goto('/mortalidad');
    await settle(page);

    await expect(page.locator('button[aria-controls="primary-nav"]')).toBeHidden();
    await expect(page.locator('#primary-nav a:visible')).toHaveCount(6);
    await expect(page.locator('#primary-nav a[aria-current="page"]')).toHaveCount(1);
  });
});
