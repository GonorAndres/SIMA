import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useDemoContext } from '../../context/useDemo';
import styles from './DemoBar.module.css';

export default function DemoBar() {
  const { t } = useTranslation();
  const { active, step, totalSteps, narrativeKey, next, prev, stop } = useDemoContext();
  const barRef = useRef<HTMLDivElement>(null);

  // The bar is fixed to the bottom, so without this it sits on top of the end
  // of the page — on a phone it wraps to three lines and buried the last
  // chart. Measured rather than hardcoded because its height depends on how
  // far the narrative wraps.
  useEffect(() => {
    if (!active) return;
    const el = barRef.current;
    if (!el) return;
    const apply = () => {
      document.body.style.paddingBottom = `${el.offsetHeight}px`;
    };
    apply();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(apply) : null;
    ro?.observe(el);
    return () => {
      ro?.disconnect();
      document.body.style.paddingBottom = '';
    };
  }, [active, narrativeKey]);

  if (!active) return null;

  return (
    <div className={styles.bar} ref={barRef}>
      <div className={styles.inner}>
        <button className={styles.stopBtn} onClick={stop}>
          {t('demo.stop')}
        </button>

        <div className={styles.narrative}>
          {t(narrativeKey)}
        </div>

        <div className={styles.controls}>
          <button
            className={styles.navBtn}
            onClick={prev}
            disabled={step === 0}
            aria-label={t('demo.prev')}
          >
            <span aria-hidden="true">&#8592;</span>
          </button>

          {/* "3 / 8" reads as a fraction to a screen reader, so the spoken
              form is supplied separately from the printed one. */}
          <span className={styles.counter}>
            <span aria-hidden="true">
              {step + 1} / {totalSteps}
            </span>
            <span className={styles.srOnly}>
              {t('demo.progress', { step: step + 1, total: totalSteps })}
            </span>
          </span>

          <button
            className={styles.navBtn}
            onClick={next}
            disabled={step === totalSteps - 1}
            aria-label={t('demo.next')}
          >
            <span aria-hidden="true">&#8594;</span>
          </button>
        </div>
      </div>
    </div>
  );
}
