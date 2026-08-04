import { describe, expect, it } from 'vitest';
import { compactMoney, countryKey, countryLabel, wholeMoney } from './format';

/**
 * THEORY: these helpers exist because the same figure was rendering differently
 * on different pages -- the SCR total as "$809.2K" on /scr and "$809,207" on
 * /metodologia, and a row mixing "$1051K" with "$4.79M". The tests below pin
 * the properties that made those bugs possible.
 */

describe('compactMoney', () => {
  it('switches to millions at 1M so neighbouring tiles share a scale', () => {
    // The old bug: 1.05M rendered as "$1051K" beside a sibling reading "$4.79M".
    expect(compactMoney(1_051_000)).toBe('$1.05M');
    expect(compactMoney(4_785_472)).toBe('$4.79M');
  });

  it('keeps thousands below the boundary', () => {
    expect(compactMoney(809_207)).toBe('$809.2K');
    expect(compactMoney(999_999)).toBe('$1000.0K');
  });

  it('is continuous across the boundary', () => {
    expect(compactMoney(1_000_000)).toBe('$1.00M');
  });

  it('handles negative amounts on magnitude, not sign', () => {
    expect(compactMoney(-2_500_000)).toBe('$-2.50M');
  });

  it('does not throw on zero', () => {
    expect(compactMoney(0)).toBe('$0.0K');
  });
});

describe('wholeMoney', () => {
  it('drops centavos, which are noise on an annual premium', () => {
    expect(wholeMoney(18_824.08)).toBe('$18,824');
    expect(wholeMoney(7_699.92)).toBe('$7,700');
  });

  it('groups thousands so long figures stay readable', () => {
    expect(wholeMoney(1_234_567)).toBe('$1,234,567');
  });
});

describe('countryKey', () => {
  it('matches regardless of accents, because the API sends Spanish labels', () => {
    // The backend emits "México" / "España"; the frontend must still resolve
    // them without depending on exact orthography.
    expect(countryKey('México')).toBe('mexico');
    expect(countryKey('Mexico')).toBe('mexico');
    expect(countryKey('España')).toBe('spain');
    expect(countryKey('Espana')).toBe('spain');
  });

  it('accepts either language for the United States', () => {
    expect(countryKey('Estados Unidos')).toBe('usa');
    expect(countryKey('United States')).toBe('usa');
    expect(countryKey('USA')).toBe('usa');
  });

  it('is case insensitive', () => {
    expect(countryKey('MÉXICO')).toBe('mexico');
    expect(countryKey('españa')).toBe('spain');
  });

  it('returns null for anything it does not recognise', () => {
    // Callers fall back to the raw label; silently mapping to a wrong country
    // would be far worse than showing the untranslated string.
    expect(countryKey('Canada')).toBeNull();
    expect(countryKey('')).toBeNull();
  });
});

describe('countryLabel', () => {
  const t = (key: string) =>
    ({
      'tables.countries.mexico': 'Mexico',
      'tables.countries.usa': 'United States',
      'tables.countries.spain': 'Spain',
    })[key] ?? key;

  it('translates a recognised country', () => {
    expect(countryLabel(t, 'México')).toBe('Mexico');
    expect(countryLabel(t, 'Estados Unidos')).toBe('United States');
  });

  it('passes an unrecognised label straight through', () => {
    expect(countryLabel(t, 'Canada')).toBe('Canada');
  });
});
