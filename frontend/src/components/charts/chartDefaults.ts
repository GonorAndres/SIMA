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
