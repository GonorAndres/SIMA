import { useSyncExternalStore } from 'react';

/**
 * Subscribes to a CSS media query.
 *
 * `useSyncExternalStore` rather than `useState` + effect: the first paint then
 * already knows the answer, so a chart never renders its desktop layout and
 * flips a frame later.
 */
export default function useMediaQuery(query: string): boolean {
  const subscribe = (onChange: () => void) => {
    if (typeof window === 'undefined' || !window.matchMedia) return () => {};
    const mql = window.matchMedia(query);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  };

  const getSnapshot = () =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia(query).matches
      : false;

  // Server render has no viewport; desktop is the safer assumption because it
  // never hides controls that the client then has to restore.
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}

/**
 * True below --bp-md (768px): the phone/large-phone range where charts must
 * drop their toolbars and give the page back its vertical scroll.
 */
export function useIsCompact(): boolean {
  return useMediaQuery('(max-width: 767px)');
}
