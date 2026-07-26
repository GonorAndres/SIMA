import { lazy, Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import TopNav from './components/layout/TopNav';
import Footer from './components/layout/Footer';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoadingState from './components/common/LoadingState';
import { DemoProvider } from './context/DemoContext';
import DemoBar from './components/demo/DemoBar';

const Inicio = lazy(() => import('./pages/Inicio'));
const Mortalidad = lazy(() => import('./pages/Mortalidad'));
const Tarificacion = lazy(() => import('./pages/Tarificacion'));
const SCR = lazy(() => import('./pages/SCR'));
const Sensibilidad = lazy(() => import('./pages/Sensibilidad'));
const Metodologia = lazy(() => import('./pages/Metodologia'));

/**
 * A route change should start the new page at the top — otherwise a user
 * arriving from a long page lands mid-content with no context.
 */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  const { t } = useTranslation();

  return (
    <BrowserRouter>
      <DemoProvider>
        <ScrollToTop />
        <div className="appShell">
          <a className="skipLink" href="#main-content">
            {t('nav.skipToContent')}
          </a>
          <TopNav />
          <div className="appContent" id="main-content">
            <ErrorBoundary>
              <Suspense fallback={<LoadingState />}>
                <Routes>
                  <Route path="/" element={<Inicio />} />
                  <Route path="/mortalidad" element={<Mortalidad />} />
                  <Route path="/tarificacion" element={<Tarificacion />} />
                  <Route path="/scr" element={<SCR />} />
                  <Route path="/sensibilidad" element={<Sensibilidad />} />
                  <Route path="/metodologia" element={<Metodologia />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
          </div>
          <Footer />
          <DemoBar />
        </div>
      </DemoProvider>
    </BrowserRouter>
  );
}
