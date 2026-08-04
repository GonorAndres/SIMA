import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmptyState from './EmptyState';
import ErrorState from './ErrorState';
import LoadingState from './LoadingState';
import { renderWithProviders, setLanguage } from '../../test/render';

beforeEach(async () => {
  await setLanguage('es');
});

describe('EmptyState', () => {
  it('renders both the title and the what-to-do-next message', () => {
    // Property (ui-responsive standard): an empty panel must say what to do
    // next, not merely that nothing is here -- a blank panel reads as broken.
    renderWithProviders(
      <EmptyState
        title="Sin pólizas"
        message="Agrega una póliza con el formulario para calcular el BEL."
      />,
    );

    expect(screen.getByText('Sin pólizas')).toBeInTheDocument();
    expect(
      screen.getByText('Agrega una póliza con el formulario para calcular el BEL.'),
    ).toBeInTheDocument();
  });
});

describe('ErrorState', () => {
  it('renders the given error message', () => {
    renderWithProviders(<ErrorState message="No se pudo cargar la proyección" />);
    expect(screen.getByText('No se pudo cargar la proyección')).toBeInTheDocument();
  });

  it('falls back to a translated generic message when none is given', () => {
    // Property: the component never renders an empty panel -- with no message
    // it still tells the user something went wrong, in the active language.
    renderWithProviders(<ErrorState />);
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('renders a retry control that invokes onRetry when pressed', async () => {
    // Property: an error the user can recover from must offer the recovery --
    // a labelled button wired to the caller's retry handler.
    const user = userEvent.setup();
    const onRetry = vi.fn();
    renderWithProviders(<ErrorState message="Fallo de red" onRetry={onRetry} />);

    const retry = screen.getByRole('button', { name: 'Reintentar' });
    await user.click(retry);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('offers no retry button when there is nothing to retry', () => {
    // Property: a dead button is worse than none -- without an onRetry handler
    // no button renders.
    renderWithProviders(<ErrorState message="Fallo permanente" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('LoadingState', () => {
  it('renders the given message', () => {
    renderWithProviders(<LoadingState message="Calculando choques..." />);
    expect(screen.getByText('Calculando choques...')).toBeInTheDocument();
  });

  it('falls back to a translated loading message when none is given', () => {
    // Property: the panel is never silent while loading -- absent a custom
    // message it shows the shared translated one.
    renderWithProviders(<LoadingState />);
    expect(screen.getByText('Cargando...')).toBeInTheDocument();
  });
});
