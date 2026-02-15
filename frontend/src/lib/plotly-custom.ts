import Plotly from 'plotly.js/lib/core';
import heatmap from 'plotly.js/lib/heatmap';
import surface from 'plotly.js/lib/surface';
import waterfall from 'plotly.js/lib/waterfall';

// Core includes scatter by default. Register only the 3 additional trace types we need.
Plotly.register([heatmap, surface, waterfall]);

export default Plotly;
