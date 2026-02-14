import Plot from 'react-plotly.js';
import { defaultLayout, defaultConfig } from './chartDefaults';

interface FanChartProps {
  x: number[] | string[];
  central: number[];
  lower: number[];
  upper: number[];
  title?: string;
  xTitle?: string;
  yTitle?: string;
  height?: number;
}

export default function FanChart({ x, central, lower, upper, title, xTitle, yTitle, height = 400 }: FanChartProps) {
  const data = [
    {
      x: [...x, ...[...x].reverse()],
      y: [...upper, ...[...lower].reverse()],
      fill: 'toself' as const,
      fillcolor: 'rgba(196, 30, 58, 0.1)',
      line: { color: 'transparent' },
      showlegend: false,
      type: 'scatter' as const,
      name: 'IC',
    },
    {
      x,
      y: central,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Central',
      line: { color: '#C41E3A', width: 2 },
    },
    {
      x,
      y: upper,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Superior',
      line: { color: '#C41E3A', width: 1, dash: 'dash' as const },
    },
    {
      x,
      y: lower,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: 'Inferior',
      line: { color: '#C41E3A', width: 1, dash: 'dash' as const },
    },
  ];

  const layout = {
    ...defaultLayout,
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    xaxis: { ...defaultLayout.xaxis, title: xTitle ? { text: xTitle } : undefined },
    yaxis: { ...defaultLayout.yaxis, title: yTitle ? { text: yTitle } : undefined },
    height,
    showlegend: true,
    legend: { orientation: 'h' as const, y: -0.15 },
  };

  return <Plot data={data} layout={layout} config={defaultConfig} style={{ width: '100%' }} />;
}
