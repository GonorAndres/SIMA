import { useTranslation } from 'react-i18next';

export default function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language;

  const toggle = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '0.75rem',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      fontWeight: 500,
    }}>
      <button
        onClick={() => toggle('es')}
        style={{
          padding: '4px 8px',
          border: 'none',
          borderRadius: '0',
          background: current === 'es' ? '#000' : 'transparent',
          color: current === 'es' ? '#fff' : '#9E9E9E',
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
        }}
      >
        ES
      </button>
      <span style={{ color: '#E0E0E0' }}>|</span>
      <button
        onClick={() => toggle('en')}
        style={{
          padding: '4px 8px',
          border: 'none',
          borderRadius: '0',
          background: current === 'en' ? '#000' : 'transparent',
          color: current === 'en' ? '#fff' : '#9E9E9E',
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
        }}
      >
        EN
      </button>
    </div>
  );
}
