import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import styles from './Footer.module.css';

type HealthPayload = {
  data_source: string;
  // Ventana de años realmente ajustada. Antes el pie decia "1990-2024", pero
  // todos los pipelines se ajustan con year_min=1990 / year_max=2019
  // (backend/api/services/precomputed.py). En lugar de corregir el rango a mano
  // lo leemos del backend, para que el pie no pueda volver a desviarse del
  // modelo. Viene de /health y no de /mortality/data/summary porque el bloque
  // de atribucion HMD remite a esta insignia: con dos peticiones, una podia
  // fallar y dejar el texto apuntando a una insignia ausente.
  year_range?: [number, number] | null;
};

export default function Footer() {
  const { t } = useTranslation();
  const [dataSource, setDataSource] = useState<string | null>(null);
  const [yearRange, setYearRange] = useState<[number, number] | null>(null);

  useEffect(() => {
    api.get<HealthPayload>('/health').then((res) => {
      setDataSource(res.data.data_source);
      const range = res.data.year_range;
      if (range && range.length === 2) setYearRange([range[0], range[1]]);
    }).catch(() => {});
  }, []);

  return (
    <footer className={styles.footer}>
      <div className={styles.topRow}>
        <span>SIMA · Sistema Integral de Modelación Actuarial · {new Date().getFullYear()}</span>
        {dataSource && (
          <span className={styles.dataSource}>
            {dataSource === 'real'
              ? (yearRange
                  ? t('footer.dataMexico', { yearFrom: yearRange[0], yearTo: yearRange[1] })
                  : 'INEGI/CONAPO')
              : t('footer.dataDemo')}
          </span>
        )}
      </div>

      {/* Atribucion HMD obligatoria (CC BY 4.0). Las series de EUA y España son
          datos reales del Human Mortality Database, asi que la cita tiene que
          aparecer en el sitio desplegado y no solo en el README. */}
      <div className={styles.attribution}>
        <p className={styles.citation}>{t('footer.hmdCitation')}</p>
        {/* La ventana ajustada solo se enuncia si el backend la reporto. Antes
            la frase remitia a "la ventana indicada arriba", y esa insignia no
            se renderiza cuando /health falla o los datos no son reales. */}
        <p className={styles.citation}>
          {t('footer.hmdLicense')} {t('footer.hmdVintage')}
          {yearRange && ` ${t('footer.hmdWindow', { yearFrom: yearRange[0], yearTo: yearRange[1] })}`}
        </p>
      </div>
    </footer>
  );
}
