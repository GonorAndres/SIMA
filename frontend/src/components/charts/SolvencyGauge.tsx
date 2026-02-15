import { useTranslation } from 'react-i18next';
import styles from './SolvencyGauge.module.css';

interface SolvencyGaugeProps {
  ratio: number;
}

export default function SolvencyGauge({ ratio }: SolvencyGaugeProps) {
  const { t } = useTranslation();
  const pct = (ratio * 100).toFixed(1);
  const isSolvent = ratio >= 1.0;
  const barColor = isSolvent ? '#2E7D32' : '#C41E3A';
  const barWidth = Math.min(ratio / 2, 1) * 100;

  return (
    <div className={styles.wrapper}>
      <div className={styles.label}>
        {t('charts.solvencyIndex')}
      </div>
      <div className={styles.value} style={{ color: barColor }}>
        {pct}%
      </div>
      <div className={styles.track}>
        <div
          className={styles.bar}
          style={{ width: `${barWidth}%`, background: barColor }}
        />
        <div className={styles.marker} />
      </div>
      <div className={styles.scale}>
        <span>0%</span>
        <span>100%</span>
        <span>200%</span>
      </div>
    </div>
  );
}
