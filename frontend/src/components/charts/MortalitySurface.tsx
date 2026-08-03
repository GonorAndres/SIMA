import { useTranslation } from 'react-i18next';
import Plot from './Plot';
import { defaultLayout, chartConfig } from './chartDefaults';
import { useIsCompact } from '../../hooks/useMediaQuery';
import styles from './MortalitySurface.module.css';

interface MortalitySurfaceProps {
  ages: number[];
  years: number[];
  values: number[][];
  title?: string;
  height?: number;
}

export default function MortalitySurface({ ages, years, values, title, height = 500 }: MortalitySurfaceProps) {
  const { t } = useTranslation();
  const isCompact = useIsCompact();

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
    // A 3D scene needs a real height to be readable at all; 380px is the
    // floor at which the three axis titles still fit on a phone.
    height: isCompact ? Math.max(380, Math.round(height * 0.76)) : height,
    // Narrower than the 2D gutters, but not zero: a rotated scene draws its
    // tick labels and axis titles right at the edge of the box, and at 0 the
    // "Edad" title was sliced in half.
    margin: isCompact ? { t: 28, r: 8, b: 24, l: 24 } : { t: 32, r: 12, b: 40, l: 48 },
    scene: {
      xaxis: { title: { text: t('charts.year') } },
      yaxis: { title: { text: t('charts.age') } },
      zaxis: { title: { text: t('charts.lnMx') } },
      // Orbit is the gesture people expect from a surface, and unlike the 2D
      // charts this drag must stay live — rotating it is the whole point.
      dragmode: 'orbit' as const,
    },
  };

  return (
    <div>
      <Plot
        data={data}
        layout={layout}
        // The modebar still goes on mobile, but chartConfig never touches the
        // scene's own dragmode, so rotation survives.
        config={chartConfig(isCompact)}
        style={{ width: '100%' }}
        useResizeHandler
      />
      {/* Nothing on a touch screen says this object can be turned. */}
      <p className={styles.hint}>{t('charts.rotateHint')}</p>
    </div>
  );
}
