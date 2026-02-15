# Session 12: Plotly.js Bundle Optimization

**Date**: 2026-02-15
**Branch**: `14feb`
**Duration**: ~1 hour

---

## Problem

The frontend produced a single 5.3 MB JavaScript chunk (1.6 MB gzip). Plotly.js was the dominant cost (~4.7 MB minified) because `react-plotly.js` imports the **full** Plotly distribution with all 50+ trace types, mapbox, geo, gl2d, and every locale. The project only uses 4 trace types: `scatter`, `heatmap`, `surface`, `waterfall`.

---

## Solution: Three-Pronged Optimization

### Prong 1: Custom Plotly Bundle (biggest win)

Replaced the full `plotly.js` import with a custom bundle using `plotly.js/lib/core` + the factory pattern from `react-plotly.js/factory`.

**New files created:**
- `frontend/src/lib/plotly-custom.ts` -- Imports `plotly.js/lib/core` (includes scatter by default), registers `heatmap`, `surface`, `waterfall` via `Plotly.register()`
- `frontend/src/lib/plotly-custom.d.ts` -- Ambient TypeScript declarations for the untyped Plotly sub-modules
- `frontend/src/components/charts/Plot.tsx` -- Central wrapper using `createPlotlyComponent(Plotly)` factory

**Modified 5 chart components** (one-line import change each):
- `LineChart.tsx`, `HeatmapChart.tsx`, `MortalitySurface.tsx`, `WaterfallChart.tsx`, `FanChart.tsx`
- Changed: `import Plot from 'react-plotly.js'` -> `import Plot from './Plot'`

**Why the factory pattern matters**: `react-plotly.js` hardcodes `import Plotly from 'plotly.js'` (the full 4.7 MB bundle). The factory (`react-plotly.js/factory`) lets us inject our custom Plotly instance with only the 4 registered trace types.

### Prong 2: Route-Based Code Splitting

Converted all 6 page imports in `App.tsx` to `React.lazy()` with a `<Suspense>` boundary using the existing `<LoadingState />` component.

**Effect**: Each page becomes its own chunk. Users visiting Metodologia never download Plotly at all.

### Prong 3: Vite manualChunks for Cache Isolation

Added `build.rollupOptions.output.manualChunks` to `vite.config.ts`:
- `plotly` chunk: any module path containing `plotly.js`
- `vendor` chunk: `react-dom`, `react/`, `react-router`

Added `optimizeDeps.include` for the 4 Plotly sub-modules (dev server CJS pre-bundling).

---

## Bug Fix: `global is not defined`

After deploying, the app crashed with `global is not defined` in the browser console. Plotly.js sub-modules reference Node's `global` variable, which doesn't exist in browsers. Webpack auto-shims this, but Vite doesn't.

**Fix**: Added `define: { global: 'globalThis' }` to `vite.config.ts`. This tells Vite to textually replace every `global` reference with `globalThis` (the browser-standard equivalent).

---

## Results

### Before
| Chunk | Size | Gzip |
|-------|------|------|
| Single monolithic bundle | 5,300 KB | 1,600 KB |

### After
| Chunk | Size | Gzip | Loads When |
|-------|------|------|------------|
| `plotly-*.js` | 1,710 KB | 572 KB | First chart page visited |
| `vendor-*.js` | 228 KB | 73 KB | Always (cached aggressively) |
| `index-*.js` (app shell) | 93 KB | 31 KB | Always |
| `useApi-*.js` (shared hooks) | 38 KB | 15 KB | First data page |
| Page chunks (x6) | 4-13 KB each | 1-5 KB | Per route |

**Key metrics:**
- Plotly chunk: **68% reduction** (4,700 KB -> 1,710 KB)
- Metodologia visit: ~335 KB total (zero Plotly loaded)
- First chart page: ~2,070 KB total (61% reduction from 5.3 MB)
- Subsequent chart pages: instant (plotly chunk cached)

---

## Files Changed

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `frontend/src/lib/plotly-custom.ts` | Custom Plotly bundle (core + 3 traces) |
| CREATE | `frontend/src/lib/plotly-custom.d.ts` | TypeScript declarations for Plotly sub-modules |
| CREATE | `frontend/src/components/charts/Plot.tsx` | Factory-pattern Plot wrapper |
| MODIFY | `frontend/src/components/charts/LineChart.tsx` | Import from local Plot |
| MODIFY | `frontend/src/components/charts/HeatmapChart.tsx` | Import from local Plot |
| MODIFY | `frontend/src/components/charts/MortalitySurface.tsx` | Import from local Plot |
| MODIFY | `frontend/src/components/charts/WaterfallChart.tsx` | Import from local Plot |
| MODIFY | `frontend/src/components/charts/FanChart.tsx` | Import from local Plot |
| MODIFY | `frontend/src/App.tsx` | React.lazy + Suspense code splitting |
| MODIFY | `frontend/vite.config.ts` | manualChunks, optimizeDeps, global shim |

---

## Verification

1. `npx tsc -b` -- zero TypeScript errors
2. `npx vite build` -- multiple chunks, plotly chunk at 1,710 KB (was 5,300 KB single chunk)
3. Local deploy via SSH tunnel -- all 5 chart types render correctly (scatter, fan, heatmap, surface, waterfall)
4. `global is not defined` bug caught and fixed during deploy testing
