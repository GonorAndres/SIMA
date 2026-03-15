import { type ReactNode, useEffect } from 'react';
import styles from './PageLayout.module.css';

interface PageLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

export default function PageLayout({ children, title, subtitle }: PageLayoutProps) {
  useEffect(() => {
    if (title) {
      document.title = `${title} -- SIMA`;
    }
    return () => { document.title = 'SIMA -- Sistema Integral de Modelacion Actuarial'; };
  }, [title]);

  return (
    <main className={styles.main}>
      {title && (
        <header className={styles.header}>
          <h1 className={styles.title}>{title}</h1>
          {subtitle && (
            <p className={styles.subtitle}>
              {subtitle}
            </p>
          )}
        </header>
      )}
      {children}
    </main>
  );
}
