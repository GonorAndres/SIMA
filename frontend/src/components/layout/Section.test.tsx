import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import Section from './Section';
import { renderWithProviders } from '../../test/render';

describe('Section', () => {
  it('renders the title as a heading and the explainer beside it', () => {
    // Property (ui-responsive standard): every content block has a heading and
    // a one-sentence explainer -- a reader must never meet a chart without
    // knowing what question it answers.
    renderWithProviders(
      <Section title="Proyección k_t" explainer="Cuánto seguirá cayendo la mortalidad.">
        <div>contenido</div>
      </Section>,
    );

    expect(screen.getByRole('heading', { name: 'Proyección k_t' })).toBeInTheDocument();
    expect(screen.getByText('Cuánto seguirá cayendo la mortalidad.')).toBeInTheDocument();
  });

  it('renders the step number so long pages keep a reading order', () => {
    renderWithProviders(
      <Section title="Graduación" explainer="Suaviza las tasas crudas." step={2}>
        <div>contenido</div>
      </Section>,
    );

    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('puts the id on the section element so rail anchor links can target it', () => {
    // Property: the SectionRail navigates via #fragment anchors; the id must
    // land on the DOM node or every rail link silently scrolls nowhere.
    const { container } = renderWithProviders(
      <Section title="Validación" explainer="Compara contra la tabla regulatoria." id="validacion">
        <div>contenido</div>
      </Section>,
    );

    const section = container.querySelector('section');
    expect(section).not.toBeNull();
    expect(section).toHaveAttribute('id', 'validacion');
  });

  it('renders its children inside the section body', () => {
    renderWithProviders(
      <Section title="Tabla" explainer="Los valores l_x por edad.">
        <table>
          <tbody>
            <tr>
              <td>l_x = 100000</td>
            </tr>
          </tbody>
        </table>
      </Section>,
    );

    expect(screen.getByText('l_x = 100000')).toBeInTheDocument();
  });

  it('renders header actions when provided', () => {
    // Property: controls passed as `actions` (tabs, toggles) appear in the
    // header so the reader finds them next to the title they affect.
    renderWithProviders(
      <Section title="Superficie" explainer="Mortalidad por edad y año." actions={<button>ES</button>}>
        <div>contenido</div>
      </Section>,
    );

    expect(screen.getByRole('button', { name: 'ES' })).toBeInTheDocument();
  });
});
