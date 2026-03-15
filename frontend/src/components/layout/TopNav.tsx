import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageToggle from '../common/LanguageToggle';
import { useDemo } from '../../context/DemoContext';
import styles from './TopNav.module.css';

const navItems = [
  { to: '/', key: 'inicio' },
  { to: '/mortalidad', key: 'mortalidad' },
  { to: '/tarificacion', key: 'tarificacion' },
  { to: '/scr', key: 'scr' },
  { to: '/sensibilidad', key: 'sensibilidad' },
  { to: '/metodologia', key: 'metodologia' },
];

export default function TopNav() {
  const { t } = useTranslation();
  const demo = useDemo();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className={styles.nav} aria-label="Main navigation">
      <div className={styles.inner}>
        <NavLink to="/" className={styles.brand} aria-label="SIMA Home">
          SIMA
        </NavLink>
        <button
          className={styles.hamburger}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
        >
          {menuOpen ? '\u2715' : '\u2630'}
        </button>
        <ul className={`${styles.links} ${menuOpen ? styles.linksOpen : ''}`}>
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `${styles.link} ${isActive ? styles.linkActive : ''}`
                }
                onClick={() => setMenuOpen(false)}
              >
                {t(`nav.${item.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>
        {demo && !demo.active && (
          <button className={styles.demoBtn} onClick={demo.start} aria-label="Start guided demo tour">
            DEMO
          </button>
        )}
        <LanguageToggle />
      </div>
    </nav>
  );
}
