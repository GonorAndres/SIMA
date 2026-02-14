import Plot from 'react-plotly.js';
import { defaultLayout, defaultConfig } from './chartDefaults';

interface Trace {
  x: number[] | string[];
  y: number[];
  name: string;
  color?: string;
}

interface LineChartProps {
  traces: Trace[];
  title?: string;
  xTitle?: string;
  yTitle?: string;
  height?: number;
}

export default function LineChart({ traces, title, xTitle, yTitle, height = 400 }: LineChartProps) {
  const data = traces.map((t) => ({
    x: t.x,
    y: t.y,
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: t.name,
    line: { color: t.color, width: 2 },
  }));

  const layout = {
    ...defaultLayout,
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    xaxis: { ...defaultLayout.xaxis, title: xTitle ? { text: xTitle } : undefined },
    yaxis: { ...defaultLayout.yaxis, title: yTitle ? { text: yTitle } : undefined },
    height,
    showlegend: traces.length > 1,
    legend: { orientation: 'h' as const, y: -0.15 },
  };

  return <Plot data={data} layout={layout} config={defaultConfig} style={{ width: '100%' }} />;
}
