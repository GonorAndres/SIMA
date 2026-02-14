import { useState, useMemo } from 'react';
import styles from './DataTable.module.css';

export interface Column {
  key: string;
  label: string;
  align?: 'left' | 'right';
  numeric?: boolean;
  format?: (value: unknown) => string;
}

interface DataTableProps {
  columns: Column[];
  data: Record<string, unknown>[];
  sortable?: boolean;
}

export default function DataTable({ columns, data, sortable = true }: DataTableProps) {
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
      const va = a[sortKey];
      const vb = b[sortKey];
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortAsc ? va - vb : vb - va;
      }
      const sa = String(va ?? '');
      const sb = String(vb ?? '');
      return sortAsc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [data, sortKey, sortAsc]);

  const formatCell = (col: Column, value: unknown): string => {
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
              <th
                key={col.key}
                className={col.align === 'right' ? styles.alignRight : ''}
                onClick={() => handleSort(col.key)}
              >
                {col.label}
                {sortable && (
                  <span className={`${styles.sortArrow} ${sortKey === col.key ? styles.sortArrowActive : ''}`}>
                    {sortKey === col.key ? (sortAsc ? '\u25B2' : '\u25BC') : '\u25B2'}
                  </span>
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
