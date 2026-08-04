import { useTranslation } from 'react-i18next';
import Plot from './Plot';
import { defaultLayout, chartConfig, chartLayout, chartLegend, chartHeight } from './chartDefaults';
import { useIsCompact } from '../../hooks/useMediaQuery';

interface FanChartProps {
  x: number[] | string[];
  central: number[];
  lower: number[];
  upper: number[];
  title?: string;
  xTitle?: string;
  yTitle?: string;
  height?: number;
  labels?: { ci?: string; central?: string; upper?: string; lower?: string };
}

export default function FanChart({ x, central, lower, upper, title, xTitle, yTitle, height = 400, labels }: FanChartProps) {
  const { t } = useTranslation();
  const isCompact = useIsCompact();

  const ciLabel = labels?.ci ?? t('charts.ci');
  const centralLabel = labels?.central ?? t('charts.central');
  const upperLabel = labels?.upper ?? t('charts.upper');
  const lowerLabel = labels?.lower ?? t('charts.lower');

  const data = [
    {
      x: [...x, ...[...x].reverse()],
      y: [...upper, ...[...lower].reverse()],
      fill: 'toself' as const,
      fillcolor: 'rgba(196, 30, 58, 0.1)',
      line: { color: 'transparent' },
      showlegend: false,
      type: 'scatter' as const,
      name: ciLabel,
    },
    {
      x,
      y: central,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: centralLabel,
      line: { color: '#C41E3A', width: 2 },
    },
    {
      x,
      y: upper,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: upperLabel,
      line: { color: '#C41E3A', width: 1, dash: 'dash' as const },
    },
    {
      x,
      y: lower,
      type: 'scatter' as const,
      mode: 'lines' as const,
      name: lowerLabel,
      line: { color: '#C41E3A', width: 1, dash: 'dash' as const },
    },
  ];

  const layout = {
    ...chartLayout(isCompact, true),
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    xaxis: { ...defaultLayout.xaxis, title: xTitle ? { text: xTitle } : undefined },
    yaxis: { ...defaultLayout.yaxis, title: yTitle ? { text: yTitle } : undefined },
    height: chartHeight(height, isCompact),
    showlegend: true,
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
