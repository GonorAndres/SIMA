import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface FormulaBlockProps {
  latex: string;
  label?: string;
}

export default function FormulaBlock({ latex, label }: FormulaBlockProps) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex, {
        throwOnError: false,
        displayMode: true,
        strict: false,
      });
    } catch {
      return latex;
    }
  }, [latex]);

  return (
    <div style={{
      background: '#F5F5F5',
      padding: '24px',
      margin: '16px 0',
      textAlign: 'center',
    }}>
      {label && (
        <div style={{
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          color: '#9E9E9E',
          letterSpacing: '0.05em',
          marginBottom: '12px',
        }}>
          {label}
        </div>
      )}
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
