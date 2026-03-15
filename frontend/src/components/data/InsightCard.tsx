import type { ReactNode } from 'react';
import styles from './InsightCard.module.css';

interface InsightCardProps {
  title?: string;
  children: ReactNode;
  variant?: 'info' | 'insight' | 'warning' | 'regulatory';
}

export default function InsightCard({ title, children, variant = 'info' }: InsightCardProps) {
  return (
    <div className={`${styles.card} ${styles[variant]}`}>
      {title && <div className={styles.title}>{title}</div>}
      <div className={styles.content}>{children}</div>
    </div>
  );
}
