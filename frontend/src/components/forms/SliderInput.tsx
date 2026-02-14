interface SliderInputProps {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
  unit?: string;
}

export default function SliderInput({ label, min, max, step, value, onChange, unit }: SliderInputProps) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        marginBottom: '8px',
      }}>
        <label style={{
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          color: '#9E9E9E',
          letterSpacing: '0.05em',
          fontWeight: 500,
        }}>
          {label}
        </label>
        <span style={{
          fontFamily: '"JetBrains Mono", monospace',
          fontSize: '0.875rem',
          fontWeight: 600,
          color: '#000',
        }}>
          {value}{unit ? ` ${unit}` : ''}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{
          width: '100%',
          appearance: 'none',
          WebkitAppearance: 'none',
          height: '4px',
          background: '#E0E0E0',
          outline: 'none',
          borderRadius: '0',
          cursor: 'pointer',
          accentColor: '#C41E3A',
        }}
      />
    </div>
  );
}
