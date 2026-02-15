import styles from './FormulaBlock.module.css';

interface FormulaBlockProps {
  src: string;
  alt: string;
  label?: string;
  description?: string;
}

export default function FormulaBlock({ src, alt, label, description }: FormulaBlockProps) {
  return (
    <div className={styles.wrapper}>
      {label && (
        <div className={styles.label}>
          {label}
        </div>
      )}
      <div className={styles.formula}>
        <img src={src} alt={alt} className={styles.formulaImg} />
      </div>
      {description && (
        <div className={styles.description}>
          {description}
        </div>
      )}
    </div>
  );
}
