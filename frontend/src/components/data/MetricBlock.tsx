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
        {/* Espacio explicito: JSX descarta el salto de linea entre ambos nodos,
            asi que sin el la copia del texto salia como "30años" o "$3.73M(78%)".
            La separacion visual la sigue dando el margin-left de .unit. */}
        {unit && ' '}
        {unit && (
          <span className={styles.unit}>
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
