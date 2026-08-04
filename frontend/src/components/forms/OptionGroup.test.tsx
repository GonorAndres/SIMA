import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OptionGroup, { type Option } from './OptionGroup';
import { renderWithProviders } from '../../test/render';

type Sex = 'male' | 'female' | 'unisex';

const options: Option<Sex>[] = [
  { value: 'male', label: 'Hombres' },
  { value: 'female', label: 'Mujeres' },
  { value: 'unisex', label: 'Unisex' },
];

describe('OptionGroup', () => {
  it('renders a radiogroup labelled with the given label', () => {
    // Property (ui-responsive standard): the "choose one of N" primitive is a
    // labelled radiogroup, so assistive tech announces what the choice is about.
    renderWithProviders(
      <OptionGroup label="Sexo" options={options} value="male" onChange={vi.fn()} />,
    );

    expect(screen.getByRole('radiogroup', { name: 'Sexo' })).toBeInTheDocument();
  });

  it('renders one radio per option and marks exactly the selected one as checked', () => {
    // Property: mutual exclusivity is visible to assistive tech via
    // aria-checked -- exactly one option is checked, the one matching `value`.
    renderWithProviders(
      <OptionGroup label="Sexo" options={options} value="female" onChange={vi.fn()} />,
    );

    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(3);
    expect(screen.getByRole('radio', { name: 'Mujeres' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Hombres' })).not.toBeChecked();
    expect(screen.getByRole('radio', { name: 'Unisex' })).not.toBeChecked();
  });

  it('calls onChange with the value of the option the user picks', async () => {
    // Property: choosing an option reports that option's typed value -- the
    // parent re-runs its calculation from it.
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <OptionGroup label="Sexo" options={options} value="male" onChange={onChange} />,
    );

    await user.click(screen.getByRole('radio', { name: 'Unisex' }));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith('unisex');
  });

  it('renders the hint saying what changes when an option is pressed', () => {
    // Property (ui-responsive standard): the hint explains the consequence of
    // the choice, so the control is never a bare row of buttons.
    renderWithProviders(
      <OptionGroup
        label="Sexo"
        hint="Cambia la tabla de mortalidad usada en el cálculo."
        options={options}
        value="male"
        onChange={vi.fn()}
      />,
    );

    expect(
      screen.getByText('Cambia la tabla de mortalidad usada en el cálculo.'),
    ).toBeInTheDocument();
  });

  it('is keyboard operable: options are reachable by Tab and selectable with the keyboard', async () => {
    // Property: the options are buttons, not native radios, so keyboard
    // support is not free -- Tab must reach them and Enter/Space must select.
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <OptionGroup label="Sexo" options={options} value="male" onChange={onChange} />,
    );

    await user.tab();
    expect(screen.getByRole('radio', { name: 'Hombres' })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole('radio', { name: 'Mujeres' })).toHaveFocus();

    await user.keyboard('{Enter}');
    expect(onChange).toHaveBeenCalledWith('female');

    await user.tab();
    expect(screen.getByRole('radio', { name: 'Unisex' })).toHaveFocus();
    await user.keyboard(' ');
    expect(onChange).toHaveBeenCalledWith('unisex');
  });
});
