import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageToggle from '../common/LanguageToggle';
import { useDemo } from '../../context/useDemo';
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
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  // Every navigation dismisses the drawer, so a tap always lands on the
  // destination page rather than leaving the menu covering it.
  const closeMenu = () => setMenuOpen(false);

  // Escape closes the drawer and returns focus to the trigger.
  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        hamburgerRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [menuOpen]);

  // Lock body scroll while the drawer covers the page.
  useEffect(() => {
    if (!menuOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, [menuOpen]);

  return (
    <nav className={styles.nav} aria-label={t('nav.ariaMain')}>
      <div className={styles.inner}>
        <NavLink
          to="/"
          className={styles.brand}
          aria-label={t('nav.ariaHome')}
          onClick={closeMenu}
        >
          SIMA
        </NavLink>

        <ul id="primary-nav" className={`${styles.links} ${menuOpen ? styles.linksOpen : ''}`}>
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `${styles.link} ${isActive ? styles.linkActive : ''}`
                }
                aria-current={pathname === item.to ? 'page' : undefined}
                onClick={closeMenu}
              >
                {t(`nav.${item.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className={styles.actions}>
          {demo && !demo.active && (
            <button className={styles.demoBtn} onClick={demo.start} aria-label={t('nav.ariaDemo')}>
              DEMO
            </button>
          )}
          <LanguageToggle />
          <button
            ref={hamburgerRef}
            className={styles.hamburger}
            onClick={() => setMenuOpen((open) => !open)}
            aria-label={menuOpen ? t('nav.ariaCloseMenu') : t('nav.ariaOpenMenu')}
            aria-expanded={menuOpen}
            aria-controls="primary-nav"
          >
            <span aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
          </button>
        </div>
      </div>

      {menuOpen && (
        <div
          className={styles.backdrop}
          onClick={closeMenu}
          aria-hidden="true"
        />
      )}
    </nav>
  );
}
