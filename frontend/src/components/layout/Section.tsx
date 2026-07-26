import { type ReactNode } from 'react';
import styles from './Section.module.css';

interface SectionProps {
  /** Section heading. */
  title: string;
  /**
   * One sentence stating what this section shows and why it matters.
   * Required by design: a reader must never meet a chart without knowing
   * what question it answers.
   */
  explainer: string;
  /** Optional step number, e.g. "1" — gives long pages a reading order. */
  step?: string | number;
  /** Optional controls rendered on the right of the header (tabs, toggles). */
  actions?: ReactNode;
  /** Passed through for the guided demo tour's scroll targets. */
  demoSection?: string;
  children: ReactNode;
}

export default function Section({
  title,
  explainer,
  step,
  actions,
  demoSection,
  children,
}: SectionProps) {
  return (
    <section className={styles.section} data-demo-section={demoSection}>
      <header className={styles.header}>
        <div className={styles.headings}>
          <div className={styles.titleRow}>
            {step !== undefined && (
              <span className={styles.step} aria-hidden="true">
                {step}
              </span>
            )}
            <h2 className={styles.title}>{title}</h2>
          </div>
          <p className={styles.explainer}>{explainer}</p>
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  );
}
