import type { Layout, Config } from 'plotly.js';

export const defaultLayout: Partial<Layout> = {
  font: {
    family: '"Inter", "Helvetica Neue", Helvetica, Arial, sans-serif',
    size: 12,
    color: '#424242',
  },
  paper_bgcolor: 'transparent',
  plot_bgcolor: '#fff',
  margin: { t: 48, r: 24, b: 48, l: 56 },
  xaxis: {
    gridcolor: '#E0E0E0',
    linecolor: '#E0E0E0',
    zerolinecolor: '#E0E0E0',
  },
  yaxis: {
    gridcolor: '#E0E0E0',
    linecolor: '#E0E0E0',
    zerolinecolor: '#E0E0E0',
  },
};

export const defaultConfig: Partial<Config> = {
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
  responsive: true,
};
