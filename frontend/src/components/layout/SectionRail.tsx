import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import styles from './SectionRail.module.css';

export interface RailItem {
  /** Matches the `id` given to the corresponding <Section>. */
  id: string;
  step: string;
  label: string;
}

interface SectionRailProps {
  items: RailItem[];
}

/**
 * "On this page" navigation for long analytical pages.
 *
 * Tracks which section is currently in view and lets the reader jump
 * straight to any of them. Items whose section has not rendered yet
 * (its data is still loading) are shown muted rather than hidden, so the
 * list never reflows under the reader.
 */
export default function SectionRail({ items }: SectionRailProps) {
  const { t } = useTranslation();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [presentIds, setPresentIds] = useState<string[]>([]);

  useEffect(() => {
    // Sections mount as their data arrives, so observe the document rather
    // than a fixed node list, and re-sync whenever the set changes.
    const visible = new Set<string>();

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        });
        // The topmost section currently on screen is the one you are reading.
        const first = items.find((item) => visible.has(item.id));
        if (first) setActiveId(first.id);
      },
      // Bias the band towards the upper half of the viewport.
      { rootMargin: '-80px 0px -55% 0px' }
    );

    const observed = new Set<Element>();
    const sync = () => {
      const found: string[] = [];
      items.forEach((item) => {
        const el = document.getElementById(item.id);
        if (!el) return;
        found.push(item.id);
        if (!observed.has(el)) {
          observer.observe(el);
          observed.add(el);
        }
      });
      setPresentIds((prev) =>
        prev.length === found.length && prev.every((id, i) => id === found[i]) ? prev : found
      );
    };

    sync();
    const mutation = new MutationObserver(sync);
    mutation.observe(document.body, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      mutation.disconnect();
    };
  }, [items]);

  const jumpTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav className={styles.rail} aria-label={t('nav.onThisPage')}>
      <p className={styles.label}>{t('nav.onThisPage')}</p>
      <ul className={styles.list}>
        {items.map((item) => {
          const present = presentIds.includes(item.id);
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => present && jumpTo(item.id)}
                disabled={!present}
                aria-current={activeId === item.id ? 'true' : undefined}
                className={[
                  styles.item,
                  activeId === item.id ? styles.itemActive : '',
                  present ? '' : styles.itemPending,
                ].join(' ')}
              >
                <span className={styles.step} aria-hidden="true">{item.step}</span>
                <span className={styles.text}>{item.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
