import { useTranslation } from 'react-i18next';
import styles from './LanguageToggle.module.css';

export default function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language;

  const toggle = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  // `startsWith` so regional tags (es-MX, en-US) still mark the right button.
  const isActive = (lang: string) => current?.startsWith(lang) ?? false;

  return (
    <div className={styles.wrapper}>
      <button
        onClick={() => toggle('es')}
        className={`${styles.btn} ${isActive('es') ? styles.btnActive : ''}`}
        // No aria-label: WCAG 2.5.3 wants the accessible name to contain the
        // visible text, so "ES" must stay the name — an aria-label of
        // "Español" would leave a voice-control user unable to say "click ES".
        // `lang` gets the code pronounced as a word, `aria-pressed` carries
        // which language is actually in force.
        aria-pressed={isActive('es')}
        lang="es"
      >
        <span className={styles.ink}>ES</span>
      </button>
      <span className={styles.separator} aria-hidden="true">|</span>
      <button
        onClick={() => toggle('en')}
        className={`${styles.btn} ${isActive('en') ? styles.btnActive : ''}`}
        aria-pressed={isActive('en')}
        lang="en"
      >
        <span className={styles.ink}>EN</span>
      </button>
    </div>
  );
}
