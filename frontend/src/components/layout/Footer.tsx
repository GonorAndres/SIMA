export default function Footer() {
  return (
    <footer style={{
      borderTop: '1px solid #E0E0E0',
      padding: '24px 48px',
      textAlign: 'center',
      color: '#9E9E9E',
      fontSize: '0.8rem',
      letterSpacing: '0.05em',
      textTransform: 'uppercase' as const,
    }}>
      SIMA -- Sistema Integral de Modelacion Actuarial -- {new Date().getFullYear()}
    </footer>
  );
}
