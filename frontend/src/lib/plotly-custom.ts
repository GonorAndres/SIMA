import Plotly from 'plotly.js/lib/core';
import bar from 'plotly.js/lib/bar';
import heatmap from 'plotly.js/lib/heatmap';
import surface from 'plotly.js/lib/surface';
import waterfall from 'plotly.js/lib/waterfall';

// Core includes scatter by default. Register only the additional trace types we need.
Plotly.register([bar, heatmap, surface, waterfall]);

export default Plotly;
