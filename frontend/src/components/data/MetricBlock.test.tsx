import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import MetricBlock from './MetricBlock';
import { renderWithProviders } from '../../test/render';

describe('MetricBlock', () => {
  it('renders the label and the value', () => {
    // Property: a metric is a label + a figure; both must be visible.
    renderWithProviders(<MetricBlock label="SCR Total" value="$568,700" />);

    expect(screen.getByText('SCR Total')).toBeInTheDocument();
    expect(screen.getByText('$568,700')).toBeInTheDocument();
  });

  it('formats numeric values with locale separators', () => {
    // Property: a raw number is presented as a readable figure, not digits
    // run together.
    renderWithProviders(<MetricBlock label="Reserva" value={1234567} />);

    expect(screen.getByText((1234567).toLocaleString())).toBeInTheDocument();
  });

  it('renders the unit separated from the value so copied text stays readable', () => {
    // Property: copying "30 años" must not yield "30años" -- there is a real
    // space character between value and unit in the DOM text.
    const { container } = renderWithProviders(<MetricBlock label="Edad" value={30} unit="años" />);

    expect(screen.getByText('años')).toBeInTheDocument();
    expect(container.textContent).toContain('30 años');
  });

  it('keeps a long figure fully present in the DOM, never truncated', () => {
    // Property: the house standard says long figures wrap rather than clip.
    // The full string must be in the document, and no truncation styling
    // (text-overflow: ellipsis / nowrap) may be applied inline to the value.
    const long = '$1,234,567,890.12';
    renderWithProviders(<MetricBlock label="Provisión técnica" value={long} />);

    const value = screen.getByText(long);
    expect(value).toBeInTheDocument();
    expect(value.textContent).toBe(long);
    expect(value.style.textOverflow).not.toBe('ellipsis');
    expect(value.style.whiteSpace).not.toBe('nowrap');
    // No title-attribute fallback either -- that pattern signals clipped text.
    expect(value).not.toHaveAttribute('title');
  });
});
