import { useState, useMemo } from 'react';
import styles from './DataTable.module.css';

export interface Column<T = Record<string, unknown>> {
  key: keyof T & string;
  label: string;
  align?: 'left' | 'right';
  numeric?: boolean;
  format?: (value: unknown) => string;
}

interface DataTableProps<T = Record<string, unknown>> {
  columns: Column<T>[];
  data: T[];
  sortable?: boolean;
}

export default function DataTable<T extends Record<string, unknown>>({ columns, data, sortable = true }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);

  const handleSort = (key: string) => {
    if (!sortable) return;
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const va = a[sortKey as keyof T];
      const vb = b[sortKey as keyof T];
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortAsc ? va - vb : vb - va;
      }
      const sa = String(va ?? '');
      const sb = String(vb ?? '');
      return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [data, sortKey, sortAsc]);

  const formatCell = (col: Column<T>, value: unknown): string => {
    if (col.format) return col.format(value);
    if (typeof value === 'number') return value.toLocaleString();
    return String(value ?? '');
  };

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((col) => (
              // aria-sort tells a screen reader which column orders the table
              // and in which direction; the arrow glyph alone conveys that to
              // sighted users only.
              <th
                key={col.key}
                className={col.align === 'right' ? styles.alignRight : ''}
                aria-sort={
                  !sortable || sortKey !== col.key
                    ? undefined
                    : sortAsc
                      ? 'ascending'
                      : 'descending'
                }
              >
                {sortable ? (
                  // A real button, not an onClick on the <th>. The header was
                  // clickable but not focusable, so sorting was unreachable by
                  // keyboard and had no focus ring.
                  <button
                    type="button"
                    className={styles.sortButton}
                    onClick={() => handleSort(col.key)}
                  >
                    {col.label}
                    <span
                      aria-hidden="true"
                      className={`${styles.sortArrow} ${sortKey === col.key ? styles.sortArrowActive : ''}`}
                    >
                      {sortKey === col.key ? (sortAsc ? '\u25B2' : '\u25BC') : '\u25B2'}
                    </span>
                  </button>
                ) : (
                  col.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={[
                    col.align === 'right' ? styles.alignRight : '',
                    col.numeric ? styles.mono : '',
                  ].join(' ')}
                >
                  {formatCell(col, row[col.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
