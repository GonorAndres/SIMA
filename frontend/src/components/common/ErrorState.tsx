import { useTranslation } from 'react-i18next';
import styles from './ErrorState.module.css';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div className={styles.wrapper}>
      <div className={styles.message}>{message ?? t('common.error')}</div>
      {onRetry && (
        <button className={styles.retryBtn} onClick={onRetry}>
          {t('common.retry')}
        </button>
      )}
    </div>
  );
}
