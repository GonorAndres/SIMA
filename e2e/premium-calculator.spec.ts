import { test, expect, type Page } from '@playwright/test';

/**
 * Helper: navigate to tarificacion and wait for form to be ready.
 */
async function goToCalculator(page: Page) {
  await page.goto('/tarificacion');
  await page.waitForLoadState('load');
  await page.waitForTimeout(1000);
}

/**
 * Helper: select product type from the first <select> on the form.
 * Values: 'whole_life', 'term', 'endowment'
 */
async function selectProduct(page: Page, value: string) {
  const selects = page.locator('form select');
  await selects.first().selectOption(value);
}

/**
 * Helper: select sex from the second <select> on the form.
 * Values: 'male', 'female', 'unisex'
 */
async function selectSex(page: Page, value: string) {
  const selects = page.locator('form select');
  await selects.nth(1).selectOption(value);
}

/**
 * Helper: set the age slider value.
 * The age slider is the first input[type="range"] in the form (min=20, max=70).
 */
async function setAge(page: Page, age: number) {
  const ageSlider = page.locator('form input[type="range"]').first();
  await ageSlider.fill(String(age));
}

/**
 * Helper: set the sum assured value.
 */
async function setSumAssured(page: Page, amount: number) {
  const input = page.locator('form input[type="number"]');
  await input.fill(String(amount));
}

/**
 * Helper: set the interest rate slider.
 * The interest rate slider is the last input[type="range"] in the form (min=0.01, max=0.10).
 */
async function setInterestRate(page: Page, rate: number) {
  const sliders = page.locator('form input[type="range"]');
  const count = await sliders.count();
  await sliders.nth(count - 1).fill(String(rate));
}

/**
 * Helper: set term slider (only visible for term/endowment products).
 * Term slider appears between age and interest rate sliders.
 */
async function setTerm(page: Page, termYears: number) {
  const sliders = page.locator('form input[type="range"]');
  // When term is visible: age=0, term=1, interest=2
  await sliders.nth(1).fill(String(termYears));
}

/**
 * Helper: click the calculate button and wait for API response.
 */
async function clickCalculate(page: Page) {
  const button = page.locator('form button[type="submit"]');
  await button.click();

  // Wait for the API response
  await page.waitForTimeout(3000);
}

/**
 * Helper: extract the premium value from the result panel.
 * Looks for text matching a currency pattern like "$7,645.06" or "7645.06".
 */
async function extractPremium(page: Page): Promise<number> {
  // Look for the premium value near "Prima anual neta" or similar label
  const resultText = await page.locator('body').textContent() || '';

  // Match patterns like "$7,645.06" or "$ 7,645.06" or "7,645.06"
  const premiumMatch = resultText.match(/Prima anual neta[^$]*\$\s*([\d,]+\.?\d*)/i)
    || resultText.match(/Annual premium[^$]*\$\s*([\d,]+\.?\d*)/i)
    || resultText.match(/Prima[^$]*\$\s*([\d,]+\.?\d*)/);

  if (!premiumMatch) {
    // Try finding any dollar amount in result area
    const amounts = resultText.match(/\$\s*([\d,]+\.\d{2})/g);
    if (amounts && amounts.length > 0) {
      return parseFloat(amounts[0].replace(/[$,\s]/g, ''));
    }
    throw new Error('Could not extract premium value from page');
  }

  return parseFloat(premiumMatch[1].replace(/,/g, ''));
}

/**
 * Helper: calculate premium with given parameters and return the value.
 */
async function calculatePremium(
  page: Page,
  params: {
    product?: string;
    sex?: string;
    age?: number;
    sumAssured?: number;
    interestRate?: number;
    term?: number;
  }
): Promise<number> {
  if (params.product) await selectProduct(page, params.product);
  if (params.sex) await selectSex(page, params.sex);
  if (params.age) await setAge(page, params.age);
  if (params.sumAssured) await setSumAssured(page, params.sumAssured);
  if (params.interestRate) await setInterestRate(page, params.interestRate);
  if (params.term) await setTerm(page, params.term);

  await clickCalculate(page);
  return extractPremium(page);
}

test.describe('Premium Calculator -- Form Mechanics', () => {
  test('calculator form is visible on tarificacion page', async ({ page }) => {
    await goToCalculator(page);

    await expect(page.locator('form')).toBeVisible();
    await expect(page.locator('form select').first()).toBeVisible();
    await expect(page.locator('form button[type="submit"]')).toBeVisible();
  });

  test('product dropdown has three options', async ({ page }) => {
    await goToCalculator(page);

    const productSelect = page.locator('form select').first();
    const options = productSelect.locator('option');
    await expect(options).toHaveCount(3);
  });

  test('sex dropdown has three options', async ({ page }) => {
    await goToCalculator(page);

    const sexSelect = page.locator('form select').nth(1);
    const options = sexSelect.locator('option');
    await expect(options).toHaveCount(3);
  });

  test('default values produce valid result', async ({ page }) => {
    await goToCalculator(page);
    await clickCalculate(page);

    const premium = await extractPremium(page);
    expect(premium).toBeGreaterThan(0);
  });

  test('result panel shows prima anual neta label', async ({ page }) => {
    await goToCalculator(page);
    await clickCalculate(page);

    const bodyText = await page.locator('body').textContent() || '';
    const hasPremiumLabel = bodyText.includes('Prima anual neta') || bodyText.includes('Annual premium');
    expect(hasPremiumLabel).toBe(true);
  });

  test('result panel shows tasa de prima', async ({ page }) => {
    await goToCalculator(page);
    await clickCalculate(page);

    const bodyText = await page.locator('body').textContent() || '';
    const hasRateLabel = bodyText.includes('Tasa de prima') || bodyText.includes('Premium rate');
    expect(hasRateLabel).toBe(true);
  });

  test('term slider appears for term product', async ({ page }) => {
    await goToCalculator(page);

    await selectProduct(page, 'term');
    await page.waitForTimeout(300);

    const sliders = page.locator('form input[type="range"]');
    // Should have 3 sliders: age, term, interest rate
    await expect(sliders).toHaveCount(3);
  });

  test('term slider hidden for whole life product', async ({ page }) => {
    await goToCalculator(page);

    await selectProduct(page, 'whole_life');
    await page.waitForTimeout(300);

    const sliders = page.locator('form input[type="range"]');
    // Should have 2 sliders: age, interest rate
    await expect(sliders).toHaveCount(2);
  });
});

test.describe('Premium Calculator -- Sex Differentiation (CRITICAL)', () => {
  test('male and female premiums must differ for whole life', async ({ page }) => {
    await goToCalculator(page);

    // Calculate male premium
    const malePremium = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    // Calculate female premium (same params, different sex)
    const femalePremium = await calculatePremium(page, {
      sex: 'female',
    });

    expect(malePremium).not.toBe(femalePremium);
    expect(malePremium).toBeGreaterThan(femalePremium);
  });

  test('male and female premiums must differ for term', async ({ page }) => {
    await goToCalculator(page);

    const malePremium = await calculatePremium(page, {
      product: 'term',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
      term: 20,
    });

    const femalePremium = await calculatePremium(page, {
      sex: 'female',
    });

    expect(malePremium).not.toBe(femalePremium);
    expect(malePremium).toBeGreaterThan(femalePremium);
  });

  test('male and female premiums must differ for endowment', async ({ page }) => {
    await goToCalculator(page);

    const malePremium = await calculatePremium(page, {
      product: 'endowment',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
      term: 20,
    });

    const femalePremium = await calculatePremium(page, {
      sex: 'female',
    });

    expect(malePremium).not.toBe(femalePremium);
    expect(malePremium).toBeGreaterThan(femalePremium);
  });
});

test.describe('Premium Calculator -- Age Monotonicity', () => {
  test('premium increases with age (30 vs 50)', async ({ page }) => {
    await goToCalculator(page);

    const premium30 = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    const premium50 = await calculatePremium(page, {
      age: 50,
    });

    expect(premium50).toBeGreaterThan(premium30);
  });

  test('premium increases monotonically (20, 40, 60)', async ({ page }) => {
    await goToCalculator(page);

    const premium20 = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 20,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    const premium40 = await calculatePremium(page, { age: 40 });
    const premium60 = await calculatePremium(page, { age: 60 });

    expect(premium40).toBeGreaterThan(premium20);
    expect(premium60).toBeGreaterThan(premium40);
  });
});

test.describe('Premium Calculator -- Coverage Proportionality', () => {
  test('premium is proportional to sum assured', async ({ page }) => {
    await goToCalculator(page);

    const premium1M = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    const premium2M = await calculatePremium(page, {
      sumAssured: 2000000,
    });

    // P(2M) / P(1M) should be approximately 2.0 (within 1% tolerance)
    const ratio = premium2M / premium1M;
    expect(ratio).toBeGreaterThan(1.99);
    expect(ratio).toBeLessThan(2.01);
  });
});

test.describe('Premium Calculator -- Product Ordering', () => {
  test('term is cheaper than whole life', async ({ page }) => {
    await goToCalculator(page);

    const wholeLife = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    const term = await calculatePremium(page, {
      product: 'term',
      term: 20,
    });

    expect(term).toBeLessThan(wholeLife);
  });

  test('endowment is more expensive than term', async ({ page }) => {
    await goToCalculator(page);

    const term = await calculatePremium(page, {
      product: 'term',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.05,
      term: 20,
    });

    const endowment = await calculatePremium(page, {
      product: 'endowment',
    });

    expect(endowment).toBeGreaterThan(term);
  });
});

test.describe('Premium Calculator -- Interest Rate Sensitivity', () => {
  test('lower interest rate produces higher premium', async ({ page }) => {
    await goToCalculator(page);

    const premiumLow = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 30,
      sumAssured: 1000000,
      interestRate: 0.03,
    });

    const premiumHigh = await calculatePremium(page, {
      interestRate: 0.07,
    });

    // Lower discount rate -> higher present value of benefits -> higher premium
    expect(premiumLow).toBeGreaterThan(premiumHigh);
  });
});

test.describe('Premium Calculator -- Charts', () => {
  test('reserve trajectory chart renders after calculation', async ({ page }) => {
    await goToCalculator(page);
    await clickCalculate(page);

    // Plotly charts render inside divs with class containing 'plotly' or 'js-plotly-plot'
    const plotlyCharts = page.locator('.js-plotly-plot, [class*="plotly"]');
    const chartCount = await plotlyCharts.count();
    expect(chartCount).toBeGreaterThan(0);
  });

  test('sensitivity chart renders after calculation', async ({ page }) => {
    await goToCalculator(page);
    await clickCalculate(page);

    // Should have at least 2 charts: reserve trajectory + sensitivity
    const plotlyCharts = page.locator('.js-plotly-plot, [class*="plotly"]');
    const chartCount = await plotlyCharts.count();
    expect(chartCount).toBeGreaterThanOrEqual(2);
  });
});

test.describe('Premium Calculator -- Edge Cases', () => {
  test('minimum age (20) produces valid premium', async ({ page }) => {
    await goToCalculator(page);

    const premium = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 20,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    expect(premium).toBeGreaterThan(0);
  });

  test('maximum age (70) produces valid premium', async ({ page }) => {
    await goToCalculator(page);

    const premium = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 70,
      sumAssured: 1000000,
      interestRate: 0.05,
    });

    expect(premium).toBeGreaterThan(0);
  });

  test('minimum sum assured (10000) produces valid premium', async ({ page }) => {
    await goToCalculator(page);

    const premium = await calculatePremium(page, {
      product: 'whole_life',
      sex: 'male',
      age: 30,
      sumAssured: 10000,
      interestRate: 0.05,
    });

    expect(premium).toBeGreaterThan(0);
  });
});
