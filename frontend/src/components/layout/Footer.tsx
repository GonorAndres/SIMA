import { useEffect, useState } from 'react';
import api from '../../api/client';
import styles from './Footer.module.css';

export default function Footer() {
  const [dataSource, setDataSource] = useState<string | null>(null);

  useEffect(() => {
    api.get('/health').then((res) => {
      setDataSource((res.data as { data_source: string }).data_source);
    }).catch(() => {});
  }, []);

  return (
    <footer className={styles.footer}>
      <span>SIMA -- Sistema Integral de Modelacion Actuarial -- {new Date().getFullYear()}</span>
      {dataSource && (
        <span className={styles.dataSource}>
          {dataSource === 'real' ? 'INEGI/CONAPO (1990-2024)' : 'Synthetic demo data'}
        </span>
      )}
    </footer>
  );
}
