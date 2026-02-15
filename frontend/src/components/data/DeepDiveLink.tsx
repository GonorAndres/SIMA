import { Link } from 'react-router-dom';
import styles from './DeepDiveLink.module.css';

interface DeepDiveLinkProps {
  text: string;
  to: string;
}

export default function DeepDiveLink({ text, to }: DeepDiveLinkProps) {
  return (
    <Link to={to} className={styles.link}>
      {text} &rarr;
    </Link>
  );
}
