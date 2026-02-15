import { useTranslation } from 'react-i18next';
import { useDemoContext } from '../../context/DemoContext';
import styles from './DemoBar.module.css';

export default function DemoBar() {
  const { t } = useTranslation();
  const { active, step, totalSteps, narrativeKey, next, prev, stop } = useDemoContext();

  if (!active) return null;

  return (
    <div className={styles.bar}>
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
          >
            &#8592;
          </button>

          <span className={styles.counter}>
            {step + 1} / {totalSteps}
          </span>

          <button
            className={styles.navBtn}
            onClick={next}
            disabled={step === totalSteps - 1}
          >
            &#8594;
          </button>
        </div>
      </div>
    </div>
  );
}
