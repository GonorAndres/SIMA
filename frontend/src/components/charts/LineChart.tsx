import Plot from './Plot';
import { defaultLayout, chartConfig, chartLayout, chartLegend, chartHeight } from './chartDefaults';
import { useIsCompact } from '../../hooks/useMediaQuery';

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
  const isCompact = useIsCompact();
  const data = traces.map((t) => ({
    x: t.x,
    y: t.y,
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: t.name,
    line: { color: t.color, width: 2 },
  }));

  const showlegend = traces.length > 1;
  const layout = {
    ...chartLayout(isCompact, showlegend),
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    xaxis: { ...defaultLayout.xaxis, title: xTitle ? { text: xTitle } : undefined },
    yaxis: { ...defaultLayout.yaxis, title: yTitle ? { text: yTitle } : undefined },
    height: chartHeight(height, isCompact),
    showlegend,
    legend: chartLegend(isCompact),
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
