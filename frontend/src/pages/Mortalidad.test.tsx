import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Mortalidad from './Mortalidad';
import { renderWithProviders, setLanguage } from '../test/render';
import api from '../api/client';
import type {
  GraduationResponse,
  LCDiagnosticsResponse,
  LeeCarterFitResponse,
  MortalitySurfaceResponse,
  ProjectionResponse,
  ValidationResponse,
} from '../types';

// Hermetic: everything the page fetches goes through the axios client.
vi.mock('../api/client', () => ({ default: { get: vi.fn(), post: vi.fn() } }));

// setup.ts stubs 'react-plotly.js', but Plot.tsx builds its component from
// 'react-plotly.js/factory', which that stub does not cover. Without this the
// factory mounts against the empty plotly-custom stub and throws on mount.

const apiGet = api.get as unknown as Mock;

// SectionRail tracks the visible section with IntersectionObserver, which
// jsdom does not implement (and setup.ts does not stub).

/* ── Fixtures built from the real response shapes in src/types ── */

const lcFixture: LeeCarterFitResponse = {
  ages: [20, 21, 22],
  years: [1990, 1991, 1992],
  ax: [-6.1, -6.0, -5.9],
  bx: [0.4, 0.35, 0.25],
  kt: [2.0, 0.5, -1.0],
  explained_variance: 0.775,
  drift: -1.086,
  sigma: 1.2,
  sex: 'unisex',
  validations: {},
};

// Deliberately unusual window: the section title must follow these years, not
// a hardcoded 2020-2040 (the old bug had the title disagree with the chart).
const projFixture: ProjectionResponse = {
  projected_years: [2033, 2047, 2061],
  kt_central: [-2.0, -8.0, -14.0],
  drift: -1.086,
  sigma: 1.2,
  sex: 'unisex',
  projection_year: 2061,
};

// One validation fixture per regulatory table, distinguishable by RMSE: a
// swapped key in the `validations` record would put the wrong number under a
// correctly-labelled tab, which is exactly what these detect.
function makeValidation(name: string, rmse: number): ValidationResponse {
  return {
    name,
    projection_year: 2033,
    rmse,
    max_ratio: 1.2,
    min_ratio: 0.8,
    mean_ratio: 1.01,
    n_ages: 2,
    ages: [40, 41],
    qx_ratios: [1.01, 1.02],
    qx_differences: [0.0001, 0.0002],
  };
}

const validationByTable: Record<string, ValidationResponse> = {
  cnsf: makeValidation('CNSF 2000-I', 0.111111),
  cnsf_2013: makeValidation('CNSF M 2013', 0.222222),
  emssa_97: makeValidation('EMSSAH-97', 0.333333),
};

const graduationFixture: GraduationResponse = {
  ages: [40, 41],
  raw_mx: [0.002, 0.0021],
  graduated_mx: [0.00201, 0.00209],
  residuals: [0.00001, -0.00001],
  roughness_raw: 0.0004,
  roughness_graduated: 0.0002,
  roughness_reduction: 0.5,
  lambda_param: 100,
  sex: 'unisex',
};

const surfaceFixture: MortalitySurfaceResponse = {
  ages: [40, 41],
  years: [1990, 1991],
  log_mx: [
    [-6.2, -6.25],
    [-6.1, -6.15],
  ],
};

const diagnosticsFixture: LCDiagnosticsResponse = {
  rmse: 0.01,
  max_abs_error: 0.02,
  mean_abs_error: 0.005,
  explained_variance: 0.775,
  residuals_sample: [],
};

type GetConfig = { params?: Record<string, unknown> } | undefined;

function fixtureFor(url: string, params: Record<string, unknown>): unknown {
  switch (url) {
    case '/mortality/lee-carter':
      return lcFixture;
    case '/mortality/projection':
      return projFixture;
    case '/mortality/validation':
      return validationByTable[String(params.table_type)];
    case '/mortality/graduation':
      return graduationFixture;
    case '/mortality/surface':
      return surfaceFixture;
    case '/mortality/diagnostics':
      return diagnosticsFixture;
    default:
      throw new Error(`Unexpected GET in test: ${url}`);
  }
}

function serveAllFixtures() {
  apiGet.mockImplementation(async (url: string, config: GetConfig) => ({
    data: fixtureFor(url, config?.params ?? {}),
  }));
}

const UNISEX_FALLBACK_NOTE = /no publican columna unisex/;

describe('Mortalidad', () => {
  beforeEach(async () => {
    await setLanguage('es');
    apiGet.mockReset();
    serveAllFixtures();
  });

  it('shows each reference table its own comparison numbers when its tab is selected', async () => {
    // THEORY: the three validation hooks were just collapsed into a single
    // `validations` record keyed by table. A swapped key would render, say,
    // CNSF M 2013's RMSE under the EMSSAH-97 label -- right label, wrong
    // numbers, invisible to the eye. Each tab must show the data that was
    // requested with that tab's table_type.
    const user = userEvent.setup();
    renderWithProviders(<Mortalidad />);

    // Default tab is CNSF 2000-I.
    expect(await screen.findByText('0.111111')).toBeInTheDocument();
    expect(screen.queryByText('0.222222')).not.toBeInTheDocument();
    expect(screen.queryByText('0.333333')).not.toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: 'CNSF M 2013' }));
    expect(await screen.findByText('0.222222')).toBeInTheDocument();
    expect(screen.queryByText('0.111111')).not.toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: 'EMSSAH-97 / EMSSAM-97' }));
    expect(await screen.findByText('0.333333')).toBeInTheDocument();
    expect(screen.queryByText('0.222222')).not.toBeInTheDocument();

    // And each table was actually fetched with its own table_type -- the
    // record's keys line up with the requests, not just with the labels.
    const validationCalls = apiGet.mock.calls.filter(([url]) => url === '/mortality/validation');
    const requestedTables = validationCalls.map(
      ([, config]) => (config as GetConfig)?.params?.table_type,
    );
    expect(requestedTables).toEqual(expect.arrayContaining(['cnsf', 'cnsf_2013', 'emssa_97']));
  });

  it('retries only the active tab, with that tab\'s table_type', async () => {
    // THEORY: retry used to be a ternary chain parallel to the data one; the
    // refactor must keep it pointing at the tab the user is looking at. A
    // retry that re-fired everything, or fired the wrong table_type, would
    // hide which table is actually broken.
    apiGet.mockImplementation(async (url: string, config: GetConfig) => {
      const params = config?.params ?? {};
      if (url === '/mortality/validation' && params.table_type === 'emssa_97') {
        throw new Error('EMSSA no disponible');
      }
      return { data: fixtureFor(url, params) };
    });

    const user = userEvent.setup();
    renderWithProviders(<Mortalidad />);
    expect(await screen.findByText('0.111111')).toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: 'EMSSAH-97 / EMSSAM-97' }));
    expect(await screen.findByText('EMSSA no disponible')).toBeInTheDocument();

    apiGet.mockClear();
    await user.click(screen.getByRole('button', { name: 'Reintentar' }));

    await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(1));
    expect(apiGet).toHaveBeenCalledWith(
      '/mortality/validation',
      expect.objectContaining({ params: { table_type: 'emssa_97', sex: 'unisex' } }),
    );

    // Let the (still failing) retry settle before the test ends.
    expect(await screen.findByText('EMSSA no disponible')).toBeInTheDocument();
  });

  it('shows the male-table substitution footnote only where the annex has no unisex column', async () => {
    // THEORY: with unisex selected, CNSF 2000-I and EMSSAH/M-97 comparisons
    // silently run against the male table (the annexes publish no unisex
    // column) -- the footnote is the only disclosure of that substitution.
    // CNSF M 2013 is genuinely mixta, so showing it there would be wrong too.
    const user = userEvent.setup();
    renderWithProviders(<Mortalidad />);
    expect(await screen.findByText('0.111111')).toBeInTheDocument();

    // unisex + CNSF 2000-I: substituted, footnote present.
    expect(screen.getByText(UNISEX_FALLBACK_NOTE)).toBeInTheDocument();

    // unisex + CNSF M 2013: mixta, no substitution, no footnote.
    await user.click(screen.getByRole('radio', { name: 'CNSF M 2013' }));
    expect(screen.queryByText(UNISEX_FALLBACK_NOTE)).not.toBeInTheDocument();

    // unisex + EMSSAH-97: substituted again.
    await user.click(screen.getByRole('radio', { name: 'EMSSAH-97 / EMSSAM-97' }));
    expect(screen.getByText(UNISEX_FALLBACK_NOTE)).toBeInTheDocument();

    // Explicit male selection: the comparison is genuinely male, no footnote.
    await user.click(screen.getByRole('radio', { name: 'Masculino' }));
    await waitFor(() =>
      expect(screen.queryByText(UNISEX_FALLBACK_NOTE)).not.toBeInTheDocument(),
    );
    // Let the refetch triggered by the sex change settle.
    expect(await screen.findByText('0.333333')).toBeInTheDocument();
  });

  it('titles the k_t projection section with the years the API returned', async () => {
    // THEORY: the title once said 2020-2040 while the chart plotted to 2049.
    // Feeding an unusual window proves the title follows the response, not a
    // hardcoded range.
    renderWithProviders(<Mortalidad />);
    expect(await screen.findByText(/2033-2061/)).toBeInTheDocument();
  });

  it('re-requests everything with the new sex when the sex control changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Mortalidad />);
    expect(await screen.findByText('0.111111')).toBeInTheDocument();

    apiGet.mockClear();
    await user.click(screen.getByRole('radio', { name: 'Masculino' }));

    // The page issues eight requests (six sections + two extra validation
    // tables); every one must carry the newly selected sex.
    await waitFor(() => expect(apiGet.mock.calls.length).toBe(8));
    for (const [, config] of apiGet.mock.calls) {
      expect((config as GetConfig)?.params?.sex).toBe('male');
    }
    expect(apiGet.mock.calls.map(([url]) => url)).toEqual(
      expect.arrayContaining(['/mortality/lee-carter', '/mortality/projection', '/mortality/validation']),
    );

    // Settle the in-flight refetch before the test ends.
    expect(await screen.findByText('0.111111')).toBeInTheDocument();
  });
});
