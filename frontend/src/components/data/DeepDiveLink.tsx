import { Link } from 'react-router-dom';

interface DeepDiveLinkProps {
  text: string;
  to: string;
}

export default function DeepDiveLink({ text, to }: DeepDiveLinkProps) {
  return (
    <Link
      to={to}
      style={{
        color: '#C41E3A',
        fontSize: '0.875rem',
        fontWeight: 500,
        textDecoration: 'none',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
      }}
    >
      {text} &rarr;
    </Link>
  );
}
