import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import styles from './FormulaBlock.module.css';

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
    <div className={styles.wrapper}>
      {label && (
        <div className={styles.label}>
          {label}
        </div>
      )}
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
