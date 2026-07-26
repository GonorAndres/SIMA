import { useEffect } from 'react';

/** Brand tail. Always last so it is what gets clipped first in a narrow tab. */
const BRAND = 'SIMA';

/** Shown when no page-specific title is set (home, fallback). */
export const DEFAULT_TITLE = `${BRAND} | Modelacion Actuarial`;

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
