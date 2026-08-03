import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PremiumForm from './PremiumForm';
import { renderWithProviders, setLanguage } from '../../test/render';

describe('PremiumForm', () => {
  beforeEach(async () => {
    await setLanguage('es');
  });

  it('offers every product the pricing API prices', async () => {
    // THEORY: the dropdown is the only way in, so a product missing here is a
    // product nobody can reach. Pure endowment was absent for exactly that
    // reason, which hid a 422 in the sensitivity panel behind it.
    renderWithProviders(<PremiumForm onSubmit={vi.fn()} loading={false} />);

    const select = screen.getAllByRole('combobox')[0];
    const values = Array.from(select.querySelectorAll('option')).map((o) => o.value);

    expect(values).toEqual(
      expect.arrayContaining(['whole_life', 'term', 'endowment', 'pure_endowment']),
    );
  });

  it('asks for a term only on the products that have one', async () => {
    // THEORY: whole life runs to death, so a term field would be meaningless;
    // the other three are finite-horizon and the API rejects them without it.
    const user = userEvent.setup();
    renderWithProviders(<PremiumForm onSubmit={vi.fn()} loading={false} />);
    const select = screen.getAllByRole('combobox')[0];

    expect(screen.queryByText('Plazo')).not.toBeInTheDocument();

    for (const product of ['term', 'endowment', 'pure_endowment']) {
      await user.selectOptions(select, product);
      expect(screen.getByText('Plazo')).toBeInTheDocument();
    }

    await user.selectOptions(select, 'whole_life');
    expect(screen.queryByText('Plazo')).not.toBeInTheDocument();
  });

  it('lets the age slider reach the ages the API prices', () => {
    // THEORY: the slider stopped at 70 while the API prices to 100, so a third
    // of the supported range was unreachable from the UI.
    renderWithProviders(<PremiumForm onSubmit={vi.fn()} loading={false} />);

    const sliders = screen.getAllByRole('slider');
    const ageSlider = sliders[0] as HTMLInputElement;

    expect(Number(ageSlider.max)).toBeGreaterThanOrEqual(90);
  });

  it('submits the term for finite products and omits it for whole life', async () => {
    // THEORY: sending term=20 on a whole life policy would be silently wrong;
    // omitting it on a term policy is a 422.
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithProviders(<PremiumForm onSubmit={onSubmit} loading={false} />);
    const select = screen.getAllByRole('combobox')[0];

    await user.click(screen.getByRole('button'));
    expect(onSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({ product_type: 'whole_life', term: undefined }),
    );

    await user.selectOptions(select, 'pure_endowment');
    await user.click(screen.getByRole('button'));
    expect(onSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({ product_type: 'pure_endowment', term: expect.any(Number) }),
    );
  });

  it('translates its labels', async () => {
    renderWithProviders(<PremiumForm onSubmit={vi.fn()} loading={false} />);
    expect(screen.getByText('Tipo de producto')).toBeInTheDocument();

    await setLanguage('en');
    renderWithProviders(<PremiumForm onSubmit={vi.fn()} loading={false} />);
    expect(screen.getAllByText('Product type').length).toBeGreaterThan(0);
  });
});
