import Plot from 'react-plotly.js';
import { defaultLayout, defaultConfig } from './chartDefaults';

interface WaterfallChartProps {
  categories: string[];
  values: number[];
  title?: string;
  height?: number;
}

export default function WaterfallChart({ categories, values, title, height = 400 }: WaterfallChartProps) {
  const measure = values.map((_, i) =>
    i === values.length - 1 ? 'total' : 'relative'
  );

  const data = [
    {
      type: 'waterfall' as const,
      x: categories,
      y: values,
      measure,
      connector: { line: { color: '#E0E0E0' } },
      increasing: { marker: { color: '#C41E3A' } },
      decreasing: { marker: { color: '#9E9E9E' } },
      totals: { marker: { color: '#000' } },
    },
  ];

  const layout = {
    ...defaultLayout,
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    height,
    showlegend: false,
  };

  return <Plot data={data} layout={layout} config={defaultConfig} style={{ width: '100%' }} />;
}
