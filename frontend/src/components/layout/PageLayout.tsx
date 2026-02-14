import type { ReactNode } from 'react';

interface PageLayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

export default function PageLayout({ children, title, subtitle }: PageLayoutProps) {
  return (
    <main style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '48px',
    }}>
      {title && (
        <header style={{ marginBottom: '48px' }}>
          <h1 style={{ fontSize: '2.441rem', fontWeight: 600 }}>{title}</h1>
          {subtitle && (
            <p style={{ color: '#9E9E9E', fontSize: '1rem', marginTop: '8px' }}>
              {subtitle}
            </p>
          )}
        </header>
      )}
      {children}
    </main>
  );
}
