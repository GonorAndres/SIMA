import { useEffect } from 'react';

/** Brand tail. Always last so it is what gets clipped first in a narrow tab. */
const BRAND = 'SIMA';

/**
 * Shown when no page-specific title is set (home, fallback).
 *
 * Must stay in sync with the <title> in frontend/index.html. React overwrites
 * document.title on mount, so a mismatch means crawlers see the index.html
 * title while a human on "/" sees this one -- which is exactly what happened
 * when index.html was corrected and this constant was not.
 */
export const DEFAULT_TITLE = 'SIMA · Mortalidad Lee-Carter y solvencia en México';

/**
 * Sets the browser tab title as `<page> | SIMA`.
 *
 * Pipe separator, most specific first, brand last, <= 60 chars.
 * Use this instead of assigning `document.title` directly so every page
 * follows the same convention.
 */
export default function usePageTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} | ${BRAND}` : DEFAULT_TITLE;
    return () => {
      document.title = DEFAULT_TITLE;
    };
  }, [title]);
}
