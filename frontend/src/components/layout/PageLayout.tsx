import { type ReactNode } from 'react';
import usePageTitle from '../../hooks/usePageTitle';
import styles from './PageLayout.module.css';

interface PageLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  /**
   * Optional "on this page" rail for long analytical pages.
   * Sits under the header on mobile and beside the content on desktop.
   */
  rail?: ReactNode;
}

export default function PageLayout({ children, title, subtitle, rail }: PageLayoutProps) {
  usePageTitle(title);

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
      {rail ? (
        // Rail first in the DOM: on mobile it belongs directly under the
        // title, and on desktop grid placement moves it to the right column.
        <div className={styles.withRail}>
          <div className={styles.rail}>{rail}</div>
          <div className={styles.content}>{children}</div>
        </div>
      ) : (
        children
      )}
    </main>
  );
}
