import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Tarificacion from './Tarificacion';
import { renderWithProviders, setLanguage } from '../test/render';
import api from '../api/client';
import type {
  CrossCountryPremiumResponse,
  ReserveResponse,
  SensitivityResponse,
} from '../types';

// Hermetic: all four submit-time requests go through the axios client.
vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

// setup.ts stubs 'react-plotly.js', but Plot.tsx builds its component from
// 'react-plotly.js/factory', which that stub does not cover.

const apiPost = api.post as unknown as Mock;

/* ── Fixtures from the real response shapes in src/types ── */

const reserveFixture = (productType: string): ReserveResponse => ({
  product_type: productType,
  issue_age: 30,
  sum_assured: 1000000,
  interest_rate: 0.05,
  term: 20,
  sex: 'male',
  annual_premium: 123456.7,
  trajectory: [
    { duration: 0, age: 30, reserve: 0 },
    { duration: 10, age: 40, reserve: 50000 },
    { duration: 20, age: 50, reserve: 0 },
  ],
});

const sensitivityFixture = (productType: string): SensitivityResponse => ({
  product_type: productType,
  age: 30,
  sum_assured: 1000000,
  results: [
    { interest_rate: 0.02, annual_premium: 20000 },
    { interest_rate: 0.05, annual_premium: 12000 },
    { interest_rate: 0.08, annual_premium: 8000 },
  ],
});

// The API sends the country names in Spanish -- that is the property under
// test in the language test below.
const crossCountryFixture = (productType: string): CrossCountryPremiumResponse => ({
  product_type: productType,
  age: 30,
  sum_assured: 1000000,
  interest_rate: 0.05,
  term: 20,
  sex: 'male',
  entries: [
    { country: 'México', annual_premium: 10000, premium_rate: 0.01, drift: -1.086, explained_var: 0.775 },
    { country: 'Estados Unidos', annual_premium: 12000, premium_rate: 0.012, drift: -1.021, explained_var: 0.855 },
    { country: 'España', annual_premium: 9000, premium_rate: 0.009, drift: -2.767, explained_var: 0.952 },
  ],
});

function serveFixtures() {
  apiPost.mockImplementation(async (url: string, body: Record<string, unknown>) => {
    const productType = String(body.product_type);
    switch (url) {
      case '/pricing/premium':
        // Echo the request like the real endpoint, so the response carries the
        // raw enum the page must translate.
        return { data: { ...body, sex: body.sex ?? 'male', annual_premium: 123456.7, premium_rate: 0.0123456 } };
      case '/pricing/reserve':
        return { data: reserveFixture(productType) };
      case '/pricing/sensitivity':
        return { data: sensitivityFixture(productType) };
      case '/pricing/cross-country':
        return { data: crossCountryFixture(productType) };
      default:
        throw new Error(`Unexpected POST in test: ${url}`);
    }
  });
}

async function submitProduct(user: ReturnType<typeof userEvent.setup>, productType?: string) {
  if (productType) {
    await user.selectOptions(screen.getAllByRole('combobox')[0], productType);
  }
  await user.click(screen.getByRole('button', { name: /CALCULAR PRIMA|CALCULATE PREMIUM/ }));
}

describe('Tarificacion', () => {
  beforeEach(async () => {
    await setLanguage('es');
    apiPost.mockReset();
    serveFixtures();
  });

  it('explains what to do before anything is calculated, with no result sections', () => {
    // THEORY: a first-time visitor sees a form and nothing else; the empty
    // state must say what pressing calculate will produce, and none of the
    // result sections may render on stale/absent data.
    renderWithProviders(<Tarificacion />);

    expect(screen.getByText('Aún no hay resultados')).toBeInTheDocument();
    expect(screen.getByText(/Completa el formulario/)).toBeInTheDocument();

    expect(screen.queryByText('Prima anual neta')).not.toBeInTheDocument();
    expect(
      screen.queryByText('Trayectoria de Reservas: Método prospectivo (tV)'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText('Comparación Internacional de Primas'),
    ).not.toBeInTheDocument();
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('renders the premium with the product name translated, not the raw enum', async () => {
    // THEORY: the API echoes product_type as an enum ('pure_endowment'); the
    // result panel showed exactly that raw string until recently. The panel
    // must show the human name in the active language.
    const user = userEvent.setup();
    renderWithProviders(<Tarificacion />);

    // Before submitting, 'Dotal Puro' exists only as the dropdown option.
    // (Regex matcher: in the result panel the name shares its element with
    // " · Edad 30", so an exact-string match would miss it.)
    expect(screen.getAllByText(/Dotal Puro/)).toHaveLength(1);

    await submitProduct(user, 'pure_endowment');

    // After: the result panel adds a second, translated occurrence.
    expect(await screen.findAllByText(/Dotal Puro/)).toHaveLength(2);
    expect(screen.queryByText('pure_endowment')).not.toBeInTheDocument();
    expect(screen.queryByText(/PURE_ENDOWMENT/)).not.toBeInTheDocument();

    // And the premium itself is shown, whole-peso formatted.
    expect(screen.getByText('$123,457')).toBeInTheDocument();
  });

  it('shows the pure endowment formula, distinct from the endowment one', async () => {
    // THEORY: pure endowment pays only on survival, so its premium has no
    // M_x term -- rendering the endowment formula under it would teach the
    // reader the wrong actuarial identity.
    const user = userEvent.setup();
    renderWithProviders(<Tarificacion />);

    await submitProduct(user, 'pure_endowment');
    expect(
      await screen.findByAltText('P = SA * D_{x+n} / (N_x - N_{x+n})'),
    ).toBeInTheDocument();
    expect(
      screen.queryByAltText('P = SA * (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})'),
    ).not.toBeInTheDocument();

    await submitProduct(user, 'endowment');
    expect(
      await screen.findByAltText('P = SA * (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})'),
    ).toBeInTheDocument();
    expect(
      screen.queryByAltText('P = SA * D_{x+n} / (N_x - N_{x+n})'),
    ).not.toBeInTheDocument();
  });

  it('renders cross-country names in the active UI language, in es and en', async () => {
    // THEORY: the API sends Spanish labels ('Estados Unidos', 'España'); the
    // page must translate them at render time, so switching language flips
    // the names without refetching. They used to leak into English prose.
    const user = userEvent.setup();
    renderWithProviders(<Tarificacion />);

    await submitProduct(user);
    expect(await screen.findByText('Comparación Internacional de Primas')).toBeInTheDocument();

    // Spanish UI: Spanish names (metric label + table cell).
    expect(screen.getAllByText('Estados Unidos').length).toBeGreaterThan(0);
    expect(screen.getAllByText('España').length).toBeGreaterThan(0);

    await setLanguage('en');

    expect(screen.queryByText('Estados Unidos')).not.toBeInTheDocument();
    expect(screen.queryByText('España')).not.toBeInTheDocument();
    expect(screen.getAllByText('United States').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Spain').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Mexico').length).toBeGreaterThan(0);
  });
});
