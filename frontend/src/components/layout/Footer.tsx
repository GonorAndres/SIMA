import styles from './Footer.module.css';

export default function Footer() {
  return (
    <footer className={styles.footer}>
      SIMA -- Sistema Integral de Modelacion Actuarial -- {new Date().getFullYear()}
    </footer>
  );
}
