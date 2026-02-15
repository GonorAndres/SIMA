import Plot from './Plot';
import { defaultLayout, defaultConfig } from './chartDefaults';

interface MortalitySurfaceProps {
  ages: number[];
  years: number[];
  values: number[][];
  title?: string;
  height?: number;
}

export default function MortalitySurface({ ages, years, values, title, height = 500 }: MortalitySurfaceProps) {
  const data = [
    {
      type: 'surface' as const,
      x: years,
      y: ages,
      z: values,
      colorscale: [
        [0, '#FFFFFF'],
        [0.25, '#F5E6E8'],
        [0.5, '#E0A0A8'],
        [0.75, '#C41E3A'],
        [1, '#6B0F1E'],
      ] as Array<[number, string]>,
      colorbar: {
        title: { text: 'ln(m_x)' },
        tickfont: { family: '"JetBrains Mono", monospace', size: 10 },
      },
    },
  ];

  const layout = {
    ...defaultLayout,
    title: title ? { text: title, font: { size: 14, color: '#000' } } : undefined,
    height,
    scene: {
      xaxis: { title: { text: 'Año' } },
      yaxis: { title: { text: 'Edad' } },
      zaxis: { title: { text: 'ln(m_x)' } },
    },
  };

  return <Plot data={data} layout={layout} config={defaultConfig} style={{ width: '100%' }} />;
}
