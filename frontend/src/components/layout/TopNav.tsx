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

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.brand}>
          SIMA
        </NavLink>
        <ul className={styles.links}>
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `${styles.link} ${isActive ? styles.linkActive : ''}`
                }
              >
                {t(`nav.${item.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>
        {demo && !demo.active && (
          <button className={styles.demoBtn} onClick={demo.start}>
            DEMO
          </button>
        )}
        <LanguageToggle />
      </div>
    </nav>
  );
}
