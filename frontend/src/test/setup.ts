import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Plotly draws with WebGL and measures real layout; jsdom provides neither, and
// importing it costs seconds per test file. Every chart renders as a labelled
// stub carrying its trace count, which is all a test should assert about a
// chart anyway -- that it received data, not how it painted it.
vi.mock('react-plotly.js', () => ({
  default: ({ data }: { data?: unknown[] }) => null,
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

afterEach(() => {
  cleanup();
});
