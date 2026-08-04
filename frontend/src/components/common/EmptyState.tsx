import styles from './EmptyState.module.css';

interface EmptyStateProps {
  title: string;
  /** Tell the user what to do next, not just that nothing is here. */
  message: string;
}

export default function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <div className={styles.empty}>
      <p className={styles.title}>{title}</p>
      <p className={styles.message}>{message}</p>
    </div>
  );
}
