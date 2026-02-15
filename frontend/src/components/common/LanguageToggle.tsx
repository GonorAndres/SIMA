import { useTranslation } from 'react-i18next';
import styles from './LanguageToggle.module.css';

export default function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language;

  const toggle = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  return (
    <div className={styles.wrapper}>
      <button
        onClick={() => toggle('es')}
        className={`${styles.btn} ${current === 'es' ? styles.btnActive : ''}`}
      >
        ES
      </button>
      <span className={styles.separator}>|</span>
      <button
        onClick={() => toggle('en')}
        className={`${styles.btn} ${current === 'en' ? styles.btnActive : ''}`}
      >
        EN
      </button>
    </div>
  );
}
