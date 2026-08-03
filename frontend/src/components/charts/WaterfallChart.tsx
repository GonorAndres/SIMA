import Plot from './Plot';
import { chartConfig, chartLayout, chartHeight } from './chartDefaults';
import { useIsCompact } from '../../hooks/useMediaQuery';

interface WaterfallChartProps {
  categories: string[];
  values: number[];
  title?: string;
  height?: number;
}

export default function WaterfallChart({ categories, values, title, height = 400 }: WaterfallChartProps) {
  const isCompact = useIsCompact();
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

  const base = chartLayout(isCompact);
  const layout = {
    ...base,
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    // Risk-module names ("Diversificación", "Tasa de interés") collide when
    // six of them share a 320px axis; tilting is what keeps them readable.
    xaxis: isCompact
      ? { ...base.xaxis, tickangle: -45, tickfont: { size: 10 } }
      : base.xaxis,
    height: chartHeight(height, isCompact),
    showlegend: false,
  };

  return (
    <Plot
      data={data}
      layout={layout}
      config={chartConfig(isCompact)}
      style={{ width: '100%' }}
      useResizeHandler
    />
  );
}
