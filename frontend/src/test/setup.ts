import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Plotly draws with WebGL and measures real layout; jsdom provides neither, and
// importing it costs seconds per test file. Charts render as nothing here: a
// test should assert that a page requested and passed on its data, which is
// observable elsewhere, never how a canvas was painted.
vi.mock('react-plotly.js', () => ({
  default: () => null,
}));

// Plot.tsx does not import react-plotly.js directly -- it imports the factory
// and binds it to the custom bundle. Stubbing only the package above left the
// REAL factory in play, bound to an empty stub, so any test mounting a chart
// blew up somewhere inside Plotly instead of rendering nothing.
vi.mock('react-plotly.js/factory', () => ({
  default: () => () => null,
}));

vi.mock('../lib/plotly-custom', () => ({ default: {} }));

// jsdom implements neither, and both are used by layout components.
window.matchMedia =
  window.matchMedia ||
  ((query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }) as unknown as MediaQueryList);

window.scrollTo = window.scrollTo || vi.fn();

if (!window.ResizeObserver) {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

// SectionRail observes headings to highlight the active section. jsdom ships no
// IntersectionObserver, so without this every page test carrying a rail throws
// on mount -- before reaching whatever it meant to assert.
if (!window.IntersectionObserver) {
  window.IntersectionObserver = class {
    readonly root = null;
    readonly rootMargin = '';
    readonly thresholds: readonly number[] = [];
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  } as unknown as typeof IntersectionObserver;
}

afterEach(() => {
  cleanup();
});
