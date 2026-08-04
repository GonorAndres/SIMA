import { describe, expect, it } from 'vitest';
import { renderHook } from '@testing-library/react';
import usePageTitle, { DEFAULT_TITLE } from './usePageTitle';
import i18n from '../i18n';

/**
 * THEORY: the UI standard mandates browser tab titles of the form
 * "<Page> | SIMA" -- pipe separator only (never a dash or em-dash), page name
 * first so it survives tab clipping, brand last, <= 60 chars total. Every page
 * goes through this hook (via PageLayout), so pinning the hook pins the whole
 * site's tab titles.
 */

describe('usePageTitle', () => {
  it('sets the tab title as "<Page> | SIMA", page name first, brand last', () => {
    renderHook(() => usePageTitle('Mortalidad'));
    expect(document.title).toBe('Mortalidad | SIMA');
  });

  it('separates with a pipe, never a dash or em-dash', () => {
    renderHook(() => usePageTitle('Tarificación'));
    expect(document.title).toContain(' | ');
    expect(document.title).not.toMatch(/—|–| - /);
  });

  it('falls back to the shared default title when no page title is given (home)', () => {
    renderHook(() => usePageTitle());
    expect(document.title).toBe(DEFAULT_TITLE);
  });

  it('restores the default title on unmount, so leaving a page never strands its title', () => {
    const { unmount } = renderHook(() => usePageTitle('RCS'));
    expect(document.title).toBe('RCS | SIMA');
    unmount();
    expect(document.title).toBe(DEFAULT_TITLE);
  });

  it('follows title changes across re-renders', () => {
    const { rerender } = renderHook(({ title }: { title?: string }) => usePageTitle(title), {
      initialProps: { title: 'Mortalidad' as string | undefined },
    });
    expect(document.title).toBe('Mortalidad | SIMA');

    rerender({ title: 'Sensibilidad' });
    expect(document.title).toBe('Sensibilidad | SIMA');
  });

  it('keeps every real page title within 60 characters in both languages', () => {
    // The hook cannot clamp arbitrary input, so pin the actual inputs: the
    // page titles PageLayout feeds it, in both languages, brand tail included.
    const pageKeys = ['mortalidad', 'tarificacion', 'scr', 'sensibilidad', 'metodologia'];
    const tooLong: string[] = [];
    for (const lng of ['es', 'en'] as const) {
      const bundle = i18n.getResourceBundle(lng, 'translation') as Record<
        string,
        { title?: string }
      >;
      for (const key of pageKeys) {
        const title = bundle[key]?.title;
        expect(title, `${lng}:${key}.title must exist`).toBeTruthy();
        const composed = `${title} | SIMA`;
        if (composed.length > 60) tooLong.push(`${lng}:${key} -> "${composed}"`);
      }
    }
    expect(tooLong, 'tab titles exceeding 60 characters').toEqual([]);

    // The home/fallback title obeys the same length budget.
    expect(DEFAULT_TITLE.length).toBeLessThanOrEqual(60);
  });
});
