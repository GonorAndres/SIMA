import styles from './SliderInput.module.css';

interface SliderInputProps {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
  unit?: string;
  formatValue?: (v: number) => string;
}

export default function SliderInput({ label, min, max, step, value, onChange, unit, formatValue }: SliderInputProps) {
  const display = formatValue ? formatValue(value) : `${value}${unit ? ` ${unit}` : ''}`;

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <label className={styles.label}>
          {label}
        </label>
        <span className={styles.display}>
          {display}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={styles.slider}
      />
    </div>
  );
}
