interface SolvencyGaugeProps {
  ratio: number;
}

export default function SolvencyGauge({ ratio }: SolvencyGaugeProps) {
  const pct = (ratio * 100).toFixed(1);
  const isSolvent = ratio >= 1.0;
  const barColor = isSolvent ? '#2E7D32' : '#C41E3A';
  const barWidth = Math.min(ratio / 2, 1) * 100;

  return (
    <div style={{ padding: '16px 0' }}>
      <div style={{
        textTransform: 'uppercase',
        fontSize: '0.75rem',
        color: '#9E9E9E',
        letterSpacing: '0.05em',
        marginBottom: '8px',
        fontWeight: 500,
      }}>
        INDICE DE SOLVENCIA
      </div>
      <div style={{
        fontSize: '2.441rem',
        fontFamily: '"JetBrains Mono", monospace',
        fontWeight: 700,
        color: barColor,
        lineHeight: 1,
        marginBottom: '12px',
      }}>
        {pct}%
      </div>
      <div style={{
        width: '100%',
        height: '8px',
        background: '#F5F5F5',
        position: 'relative',
      }}>
        <div style={{
          width: `${barWidth}%`,
          height: '100%',
          background: barColor,
          transition: 'width 0.3s ease',
        }} />
        {/* 100% marker */}
        <div style={{
          position: 'absolute',
          left: '50%',
          top: '-4px',
          bottom: '-4px',
          width: '2px',
          background: '#000',
        }} />
      </div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginTop: '4px',
        fontSize: '0.7rem',
        color: '#9E9E9E',
        fontFamily: '"JetBrains Mono", monospace',
      }}>
        <span>0%</span>
        <span>100%</span>
        <span>200%</span>
      </div>
    </div>
  );
}
