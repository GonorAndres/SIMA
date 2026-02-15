import styles from './MetricBlock.module.css';

interface MetricBlockProps {
  label: string;
  value: string | number;
  unit?: string;
}

export default function MetricBlock({ label, value, unit }: MetricBlockProps) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.label}>
        {label}
      </div>
      <div className={styles.value}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {unit && (
          <span className={styles.unit}>
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
