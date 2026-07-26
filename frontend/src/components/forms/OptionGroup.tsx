import { useId } from 'react';
import styles from './OptionGroup.module.css';

export interface Option<T extends string> {
  value: T;
  label: string;
}

interface OptionGroupProps<T extends string> {
  /** What the choice is about, e.g. "Sexo". */
  label: string;
  /** What changes when the user picks an option. Shown below the options. */
  hint?: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Compact variant for use inside a Section header. */
  inline?: boolean;
}

/**
 * A labelled, accessible set of mutually-exclusive options.
 *
 * Uses the radiogroup role rather than tablist: these buttons re-run a
 * calculation, they do not switch between already-rendered panels.
 */
export default function OptionGroup<T extends string>({
  label,
  hint,
  options,
  value,
  onChange,
  inline = false,
}: OptionGroupProps<T>) {
  const labelId = useId();

  return (
    <div className={styles.group} style={inline ? { marginBottom: 0 } : undefined}>
      <span className={styles.label} id={labelId}>
        {label}
      </span>
      <div className={styles.options} role="radiogroup" aria-labelledby={labelId}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={value === option.value}
            className={`${styles.option} ${value === option.value ? styles.optionActive : ''}`}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {hint && !inline && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
