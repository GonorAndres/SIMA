import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
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

export default function App() {
  return (
    <BrowserRouter>
      <DemoProvider>
        <div className="appShell">
          <TopNav />
          <div className="appContent">
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
