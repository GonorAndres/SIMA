import { afterEach, describe, expect, it } from 'vitest';
import { act } from '@testing-library/react';
import i18n from './i18n';

/**
 * THEORY: src/i18n.ts holds two parallel trees (~460 keys each) edited by many
 * hands. i18next fails silently -- a key missing in one language renders the
 * fallback or the raw key path, and a placeholder present in only one language
 * renders as literal "{{year}}" text. None of that throws, so only a structural
 * audit of the actual resource objects catches it. Every assertion below is
 * phrased so its failure message lists the offending key paths.
 */

type Tree = { [key: string]: string | Tree };

const es = i18n.getResourceBundle('es', 'translation') as Tree;
const en = i18n.getResourceBundle('en', 'translation') as Tree;

/** Flatten a resource tree into { 'dot.path': leafValue }. */
function flatten(tree: Tree, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null) {
      Object.assign(out, flatten(value, path));
    } else {
      out[path] = String(value);
    }
  }
  return out;
}

const esFlat = flatten(es);
const enFlat = flatten(en);

/** The set of {{...}} interpolation tokens in a string, sorted for comparison. */
function placeholders(value: string): string {
  return [...value.matchAll(/\{\{\s*([^}]+?)\s*\}\}/g)]
    .map((m) => m[1])
    .sort()
    .join(', ');
}

describe('i18n resource integrity', () => {
  it('has a real amount of keys in both trees (guards the flattener itself)', () => {
    // If the bundle lookup or flattener silently broke, every test below would
    // pass vacuously over empty objects. ~460 keys existed when this was written.
    expect(Object.keys(esFlat).length).toBeGreaterThan(400);
    expect(Object.keys(enFlat).length).toBeGreaterThan(400);
  });

  it('every Spanish key path exists in English', () => {
    const missingInEn = Object.keys(esFlat).filter((path) => !(path in enFlat));
    expect(missingInEn, 'key paths present in es but missing in en').toEqual([]);
  });

  it('every English key path exists in Spanish', () => {
    const missingInEs = Object.keys(enFlat).filter((path) => !(path in esFlat));
    expect(missingInEs, 'key paths present in en but missing in es').toEqual([]);
  });

  it('no key has an empty or whitespace-only value in either language', () => {
    const empty = [
      ...Object.entries(esFlat).map(([p, v]) => [`es:${p}`, v] as const),
      ...Object.entries(enFlat).map(([p, v]) => [`en:${p}`, v] as const),
    ]
      .filter(([, v]) => v.trim() === '')
      .map(([p]) => p);
    expect(empty, 'keys whose value is empty or whitespace-only').toEqual([]);
  });

  it('interpolation placeholders match between languages for every key', () => {
    // A {{token}} present in only one language is never an error at runtime:
    // i18next just prints it literally ("{{yearFrom}}") to the user.
    const mismatched = Object.keys(esFlat)
      .filter((path) => path in enFlat)
      .filter((path) => placeholders(esFlat[path]) !== placeholders(enFlat[path]))
      .map(
        (path) =>
          `${path}: es has [${placeholders(esFlat[path])}], en has [${placeholders(enFlat[path])}]`,
      );
    expect(mismatched, 'keys whose {{placeholder}} sets differ between es and en').toEqual([]);
  });

  it('no English prose is a byte-identical copy of the Spanish', () => {
    // Catches untranslated copy-paste: any value longer than 25 chars that
    // contains a space and is identical in both trees is almost certainly
    // Spanish text shipped to English readers (or vice versa).
    //
    // Exemptions -- strings that are legitimately identical in both languages:
    const exempt = new Set<string>([
      // The HMD citation is a licensing obligation (CC BY 4.0) quoted verbatim
      // in the form mortality.org prescribes; it is not translated on purpose.
      'footer.hmdCitation',
      // Institution acronyms plus an interpolated year window -- no prose in it.
      'footer.dataMexico',
    ]);
    const identical = Object.keys(esFlat)
      .filter((path) => path in enFlat && !exempt.has(path))
      .filter(
        (path) =>
          esFlat[path] === enFlat[path] &&
          esFlat[path].length > 25 &&
          esFlat[path].includes(' '),
      );
    expect(
      identical,
      'prose identical in es and en (untranslated copy-paste, or add to the exemption list with a reason)',
    ).toEqual([]);
  });
});

describe('language switching', () => {
  afterEach(async () => {
    // i18n is a module-level singleton; leave it in Spanish for other tests.
    await act(async () => {
      await i18n.changeLanguage('es');
    });
  });

  it('updates document.documentElement.lang so screen readers switch phonetics', async () => {
    // The languageChanged listener in i18n.ts exists because the document lang
    // once stayed "es" after switching, making screen readers pronounce the
    // English UI with Spanish phonetics.
    await act(async () => {
      await i18n.changeLanguage('en');
    });
    expect(document.documentElement.lang).toBe('en');

    await act(async () => {
      await i18n.changeLanguage('es');
    });
    expect(document.documentElement.lang).toBe('es');
  });
});
