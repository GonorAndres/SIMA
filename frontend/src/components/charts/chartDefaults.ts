import type { Layout, Config } from 'plotly.js';

export const defaultLayout: Partial<Layout> = {
  font: {
    family: '"Inter", "Helvetica Neue", Helvetica, Arial, sans-serif',
    size: 12,
    color: '#424242',
  },
  paper_bgcolor: 'transparent',
  plot_bgcolor: '#fff',
  /* Small right/top gutters; left and bottom are driven by `automargin`
     below so labels fit at any width without a viewport check. */
  margin: { t: 32, r: 12, b: 40, l: 48 },
  xaxis: {
    gridcolor: '#E0E0E0',
    linecolor: '#E0E0E0',
    zerolinecolor: '#E0E0E0',
    automargin: true,
  },
  yaxis: {
    gridcolor: '#E0E0E0',
    linecolor: '#E0E0E0',
    zerolinecolor: '#E0E0E0',
    automargin: true,
  },
};

export const defaultConfig: Partial<Config> = {
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
  responsive: true,
};

/**
 * Chart config for the current viewport.
 *
 * On a phone the modebar is 24x22px of unpressable icons over the plot, and
 * `dragmode` is worse than useless: a vertical swipe that starts on the chart
 * is read as a zoom gesture, so the page stops scrolling and the reader is
 * stuck. Both are switched off below --bp-md; the chart becomes something you
 * read rather than something you fight.
 */
export function chartConfig(isCompact: boolean): Partial<Config> {
  if (!isCompact) return defaultConfig;
  return {
    ...defaultConfig,
    displayModeBar: false,
    scrollZoom: false,
    staticPlot: false,
  };
}

/**
 * Layout for the current viewport: tighter gutters so the plotting area
 * survives a 320px column, and drag disabled to match `chartConfig`.
 *
 * `hasLegend` matters because a horizontal legend below the plot lands in the
 * same band as the x-axis title once the chart is short — on a phone the two
 * printed on top of each other. Compact charts move the legend above the plot
 * and reserve the top margin for it instead.
 */
export function chartLayout(isCompact: boolean, hasLegend = false): Partial<Layout> {
  if (!isCompact) return defaultLayout;
  return {
    ...defaultLayout,
    // r:16 rather than 8 — the last x tick label ("100") is centred on the
    // axis end, so a narrower gutter makes Plotly drop it entirely.
    margin: { t: hasLegend ? 52 : 28, r: 16, b: 36, l: 40 },
    dragmode: false,
  };
}

/**
 * Legend placement to match `chartLayout`: above the plot when compact, below
 * it otherwise. Left-aligned rather than centred so it lines up with the
 * y-axis and reads as part of the same block.
 */
export function chartLegend(isCompact: boolean): Partial<Layout>['legend'] {
  return isCompact
    ? {
        orientation: 'h' as const,
        y: 1.02,
        yanchor: 'bottom' as const,
        x: 0,
        xanchor: 'left' as const,
        font: { size: 11 },
      }
    : { orientation: 'h' as const, y: -0.15 };
}

/**
 * A 400px chart eats half a phone screen and pushes the explainer out of
 * view. Shrink it, but never below the point where the axes stop being
 * legible.
 */
export function chartHeight(base: number, isCompact: boolean): number {
  return isCompact ? Math.max(260, Math.round(base * 0.72)) : base;
}
