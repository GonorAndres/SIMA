import { useId } from 'react';
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
  const id = useId();

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <label className={styles.label} htmlFor={id}>
          {label}
        </label>
        <span className={styles.display} aria-hidden="true">
          {display}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className={styles.slider}
        // The readout beside the label is the sighted user's value; this is
        // the same figure, formatted, for anyone hearing the control.
        aria-valuetext={display}
      />
    </div>
  );
}
