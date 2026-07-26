declare module 'plotly.js/lib/core' {
  // The custom core bundle exposes the same top-level API surface as the
  // full plotly.js module (newPlot, react, purge, register, ...).
  const Plotly: typeof import('plotly.js');
  export default Plotly;
}

declare module 'plotly.js/lib/heatmap' {
  const mod: object;
  export default mod;
}

declare module 'plotly.js/lib/surface' {
  const mod: object;
  export default mod;
}

declare module 'plotly.js/lib/waterfall' {
  const mod: object;
  export default mod;
}
