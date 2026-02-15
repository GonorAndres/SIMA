import Plot from './Plot';
import { defaultLayout, defaultConfig } from './chartDefaults';

interface HeatmapChartProps {
  x: number[] | string[];
  y: number[] | string[];
  z: number[][];
  title?: string;
  xTitle?: string;
  yTitle?: string;
  height?: number;
}

export default function HeatmapChart({ x, y, z, title, xTitle, yTitle, height = 400 }: HeatmapChartProps) {
  const data = [
    {
      type: 'heatmap' as const,
      x,
      y,
      z,
      colorscale: [
        [0, '#FFFFFF'],
        [0.25, '#F5E6E8'],
        [0.5, '#E0A0A8'],
        [0.75, '#C41E3A'],
        [1, '#6B0F1E'],
      ] as Array<[number, string]>,
      colorbar: {
        tickfont: { family: '"JetBrains Mono", monospace', size: 10 },
      },
    },
  ];

  const layout = {
    ...defaultLayout,
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    xaxis: { ...defaultLayout.xaxis, title: xTitle ? { text: xTitle } : undefined },
    yaxis: { ...defaultLayout.yaxis, title: yTitle ? { text: yTitle } : undefined },
    height,
  };

  return <Plot data={data} layout={layout} config={defaultConfig} style={{ width: '100%' }} />;
}
