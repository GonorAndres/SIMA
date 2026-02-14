interface MetricBlockProps {
  label: string;
  value: string | number;
  unit?: string;
}

export default function MetricBlock({ label, value, unit }: MetricBlockProps) {
  return (
    <div style={{ padding: '16px 0' }}>
      <div style={{
        textTransform: 'uppercase',
        fontSize: '0.8rem',
        color: '#9E9E9E',
        letterSpacing: '0.05em',
        fontWeight: 500,
        marginBottom: '4px',
      }}>
        {label}
      </div>
      <div style={{
        fontSize: '1.953rem',
        fontFamily: '"JetBrains Mono", monospace',
        fontVariantNumeric: 'tabular-nums',
        fontWeight: 600,
        color: '#000',
        lineHeight: 1.2,
      }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {unit && (
          <span style={{
            fontSize: '0.875rem',
            color: '#9E9E9E',
            marginLeft: '8px',
            fontWeight: 400,
          }}>
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
