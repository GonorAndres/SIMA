import { BrowserRouter, Routes, Route } from 'react-router-dom';
import TopNav from './components/layout/TopNav';
import Footer from './components/layout/Footer';
import ErrorBoundary from './components/common/ErrorBoundary';
import Inicio from './pages/Inicio';
import Mortalidad from './pages/Mortalidad';
import Tarificacion from './pages/Tarificacion';
import SCR from './pages/SCR';
import Sensibilidad from './pages/Sensibilidad';
import Metodologia from './pages/Metodologia';

export default function App() {
  return (
    <BrowserRouter>
      <div className="appShell">
        <TopNav />
        <div className="appContent">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Inicio />} />
              <Route path="/mortalidad" element={<Mortalidad />} />
              <Route path="/tarificacion" element={<Tarificacion />} />
              <Route path="/scr" element={<SCR />} />
              <Route path="/sensibilidad" element={<Sensibilidad />} />
              <Route path="/metodologia" element={<Metodologia />} />
            </Routes>
          </ErrorBoundary>
        </div>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
