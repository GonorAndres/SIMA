import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import Footer from './Footer';
import { renderWithProviders, setLanguage } from '../../test/render';
import api from '../../api/client';

// The footer's only network dependency: GET /health for the data-source badge.
vi.mock('../../api/client', () => ({
  default: { get: vi.fn() },
}));
const mockedGet = vi.mocked(api.get);

/**
 * THEORY: the USA/Spain series are real Human Mortality Database data, and
 * CC BY 4.0 makes the acknowledgement a licensing obligation -- the citation
 * must render on the deployed site, unconditionally, in every language. The
 * data-source badge, by contrast, is best-effort: it appears only when /health
 * answers, and must degrade quietly (never a broken interpolation) when it
 * does not.
 */

const HMD_CITATION =
  'HMD. Human Mortality Database. Max Planck Institute for Demographic Research (Germany), ' +
  'University of California, Berkeley (USA), and French Institute for Demographic Studies ' +
  '(France). Available at www.mortality.org.';

describe('Footer', () => {
  beforeEach(async () => {
    await setLanguage('es');
    mockedGet.mockReset();
    // Default: backend unreachable. Tests that need a healthy backend override.
    mockedGet.mockRejectedValue(new Error('backend down'));
  });

  it('renders the HMD citation even when the API is down (licensing must not depend on /health)', async () => {
    renderWithProviders(<Footer />);
    expect(await screen.findByText(HMD_CITATION)).toBeInTheDocument();
    expect(screen.getByText(/Datos HMD bajo licencia CC BY 4\.0\./)).toBeInTheDocument();
  });

  it('renders the attribution in English too, with the citation kept verbatim', async () => {
    // The citation text itself is quoted in the form mortality.org prescribes,
    // so it is identical in both languages; the license line is translated.
    await setLanguage('en');
    renderWithProviders(<Footer />);
    expect(await screen.findByText(HMD_CITATION)).toBeInTheDocument();
    expect(screen.getByText(/HMD data licensed under CC BY 4\.0\./)).toBeInTheDocument();
  });

  it('shows the fitted year window in the data badge when /health reports it', async () => {
    mockedGet.mockResolvedValue({
      data: { data_source: 'real', year_range: [1990, 2019] },
    });
    renderWithProviders(<Footer />);

    // Badge with interpolated years -- never a literal "{{yearFrom}}".
    expect(await screen.findByText('INEGI/CONAPO (1990-2019)')).toBeInTheDocument();
    // The HMD window sentence is also gated on the reported range.
    expect(
      screen.getByText(/El ajuste Lee-Carter usa la ventana común 1990-2019\./),
    ).toBeInTheDocument();
  });

  it('falls back to a plain INEGI/CONAPO badge when /health omits the year range', async () => {
    mockedGet.mockResolvedValue({ data: { data_source: 'real', year_range: null } });
    renderWithProviders(<Footer />);

    expect(await screen.findByText('INEGI/CONAPO')).toBeInTheDocument();
    // Without a reported window, the window sentence must not render at all --
    // it would otherwise assert a fit range nobody verified.
    expect(screen.queryByText(/ventana común/)).not.toBeInTheDocument();
  });

  it('labels synthetic data honestly when the backend is not serving real data', async () => {
    mockedGet.mockResolvedValue({ data: { data_source: 'mock' } });
    renderWithProviders(<Footer />);

    expect(await screen.findByText('Datos sintéticos de demostración')).toBeInTheDocument();
    expect(screen.queryByText(/INEGI\/CONAPO/)).not.toBeInTheDocument();
  });

  it('shows no data badge at all while /health is unreachable', async () => {
    renderWithProviders(<Footer />);
    // Wait for the citation so the effect has settled before asserting absence.
    await screen.findByText(HMD_CITATION);

    expect(screen.queryByText(/INEGI\/CONAPO/)).not.toBeInTheDocument();
    expect(screen.queryByText(/sintéticos/)).not.toBeInTheDocument();
  });
});
