import { describe, expect, it } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DataTable, { type Column } from './DataTable';
import { renderWithProviders } from '../../test/render';

interface Row extends Record<string, unknown> {
  name: string;
  amount: number;
}

const columns: Column<Row>[] = [
  { key: 'name', label: 'Nombre' },
  { key: 'amount', label: 'Monto', align: 'right', numeric: true },
];

const rows: Row[] = [
  { name: 'beta', amount: 100 },
  { name: 'alpha', amount: 20 },
  { name: 'gamma', amount: 3 },
];

/** First-column cell text, top to bottom — the observable row order. */
function columnText(colIndex: number): string[] {
  return screen
    .getAllByRole('row')
    .slice(1) // skip the header row
    .map((row) => within(row).getAllByRole('cell')[colIndex].textContent ?? '');
}

describe('DataTable', () => {
  it('renders every header and every row of data', () => {
    // Property: what you pass in is what the reader sees -- all column labels
    // and all row values are present in the table.
    renderWithProviders(<DataTable columns={columns} data={rows} />);

    expect(screen.getByRole('columnheader', { name: /Nombre/ })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: /Monto/ })).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(1 + rows.length);
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
    expect(screen.getByText('gamma')).toBeInTheDocument();
  });

  it('sorts rows when a column header is activated, and reverses on a second activation', async () => {
    // Property: clicking a sortable header orders the rows by that column
    // ascending; clicking again flips to descending.
    const user = userEvent.setup();
    renderWithProviders(<DataTable columns={columns} data={rows} />);

    // The sort control is a button inside the header, not the <th> itself, so
    // that it is focusable and keyboard operable.
    const nameSort = screen.getByRole('button', { name: /Nombre/ });
    await user.click(nameSort);
    expect(columnText(0)).toEqual(['alpha', 'beta', 'gamma']);

    await user.click(nameSort);
    expect(columnText(0)).toEqual(['gamma', 'beta', 'alpha']);
  });

  it('sorts numeric columns by value, not as strings', async () => {
    // Property: 3 < 20 < 100 numerically. A lexicographic sort would give
    // "100" < "20" < "3" -- the classic string-sort bug this test guards.
    const user = userEvent.setup();
    renderWithProviders(<DataTable columns={columns} data={rows} />);

    await user.click(screen.getByRole('button', { name: /Monto/ }));
    expect(columnText(1)).toEqual(['3', '20', '100']);
  });

  it('applies the column format function to each cell of that column', () => {
    // Property: a column's format() owns the rendering of its values -- the
    // raw number never leaks to the reader.
    const formatted: Column<Row>[] = [
      columns[0],
      { ...columns[1], format: (v) => `$${Number(v).toFixed(2)}` },
    ];
    renderWithProviders(<DataTable columns={formatted} data={rows} />);

    expect(screen.getByText('$100.00')).toBeInTheDocument();
    expect(screen.getByText('$20.00')).toBeInTheDocument();
    expect(screen.getByText('$3.00')).toBeInTheDocument();
    expect(screen.queryByText('100')).not.toBeInTheDocument();
  });

  it('right-aligns the cells of a right-aligned column and leaves the others alone', () => {
    // Property: numeric columns read right-aligned (the house table rule).
    // With CSS modules stubbed we assert the alignment class is applied to the
    // right column's header and cells, and absent from the text column's.
    renderWithProviders(<DataTable columns={columns} data={rows} />);

    const [nameHeader, amountHeader] = screen.getAllByRole('columnheader');
    expect(amountHeader.className).toContain('alignRight');
    expect(nameHeader.className).not.toContain('alignRight');

    const firstRowCells = within(screen.getAllByRole('row')[1]).getAllByRole('cell');
    expect(firstRowCells[1].className).toContain('alignRight');
    expect(firstRowCells[0].className).not.toContain('alignRight');
  });

  it('renders an empty table without crashing when there are no rows', () => {
    // Property: an empty dataset is a valid state -- headers still render,
    // body is simply empty. No exception, no phantom rows.
    renderWithProviders(<DataTable columns={columns} data={[]} />);

    expect(screen.getByRole('columnheader', { name: /Nombre/ })).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(1); // header only
  });

  it('lets a keyboard user sort, and announces the sort to assistive tech', async () => {
    // Property: sorting used to be an onClick on a bare <th> -- clickable but
    // not focusable, so it was unreachable without a mouse and no screen
    // reader could tell which column ordered the table.
    const user = userEvent.setup();
    renderWithProviders(<DataTable columns={columns} data={rows} />);

    const nameSort = screen.getByRole('button', { name: /Nombre/ });
    nameSort.focus();
    expect(nameSort).toHaveFocus();

    await user.keyboard('{Enter}');
    expect(columnText(0)).toEqual(['alpha', 'beta', 'gamma']);
    expect(screen.getByRole('columnheader', { name: /Nombre/ })).toHaveAttribute(
      'aria-sort',
      'ascending',
    );

    await user.keyboard('{Enter}');
    expect(columnText(0)).toEqual(['gamma', 'beta', 'alpha']);
    expect(screen.getByRole('columnheader', { name: /Nombre/ })).toHaveAttribute(
      'aria-sort',
      'descending',
    );

    // Only the active column carries aria-sort; a reader must not be told two
    // columns order the table at once.
    expect(screen.getByRole('columnheader', { name: /Monto/ })).not.toHaveAttribute('aria-sort');
  });

  it('renders a plain header with no control when sorting is disabled', () => {
    renderWithProviders(<DataTable columns={columns} data={rows} sortable={false} />);
    expect(screen.queryByRole('button', { name: /Nombre/ })).not.toBeInTheDocument();
  });
});
