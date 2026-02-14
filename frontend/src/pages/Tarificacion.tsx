import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import PremiumForm from '../components/forms/PremiumForm';
import type { PremiumRequest as PremiumFormData } from '../components/forms/PremiumForm';
import MetricBlock from '../components/data/MetricBlock';
import FormulaBlock from '../components/data/FormulaBlock';
import LineChart from '../components/charts/LineChart';
import LoadingState from '../components/common/LoadingState';
import { usePost } from '../hooks/useApi';
import type { PremiumResponse, ReserveResponse, SensitivityResponse } from '../types';
import styles from './Tarificacion.module.css';

const formulaMap: Record<string, string> = {
  whole_life: 'P = SA \\cdot \\frac{M_x}{N_x}',
  term: 'P = SA \\cdot \\frac{M_x - M_{x+n}}{N_x - N_{x+n}}',
  endowment: 'P = SA \\cdot \\frac{M_x - M_{x+n} + D_{x+n}}{N_x - N_{x+n}}',
};

const productLabels: Record<string, string> = {
  whole_life: 'Vida Entera',
  term: 'Temporal',
  endowment: 'Dotal',
};

export default function Tarificacion() {
  const { t } = useTranslation();
  const premium = usePost<PremiumFormData, PremiumResponse>('/pricing/premium');
  const reserve = usePost<PremiumFormData, ReserveResponse>('/pricing/reserve');
  const sensitivity = usePost<object, SensitivityResponse>('/pricing/sensitivity');
  const [lastRequest, setLastRequest] = useState<PremiumFormData | null>(null);

  const handleSubmit = (req: PremiumFormData) => {
    setLastRequest(req);
    premium.execute(req);
    reserve.execute(req);
    sensitivity.execute({
      product_type: req.product_type,
      age: req.age,
      sum_assured: req.sum_assured,
      term: req.term,
      rates: [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
    });
  };

  const loading = premium.loading || reserve.loading || sensitivity.loading;

  return (
    <PageLayout
      title={t('tarificacion.title')}
      subtitle={t('tarificacion.subtitle')}
    >
      <div className={styles.splitLayout}>
        <div>
          <h3 className={styles.sectionTitle}>{t('tarificacion.calcTitle')}</h3>
          <PremiumForm onSubmit={handleSubmit} loading={loading} />
        </div>

        <div>
          {premium.loading && <LoadingState />}
          {premium.error && <p style={{ color: '#C41E3A' }}>Error: {premium.error}</p>}

          {premium.data && (
            <div className={styles.resultPanel}>
              <div className={styles.productLabel}>
                {productLabels[premium.data.product_type] ?? premium.data.product_type}
                {' -- Edad '}{premium.data.age}
              </div>
              <MetricBlock
                label={t('tarificacion.annualPremium')}
                value={`$${premium.data.annual_premium.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
              />
              <MetricBlock
                label={t('tarificacion.premiumRate')}
                value={`${(premium.data.premium_rate * 100).toFixed(4)}%`}
              />

              {lastRequest && formulaMap[lastRequest.product_type] && (
                <FormulaBlock
                  latex={formulaMap[lastRequest.product_type]}
                  label={t('tarificacion.formula')}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {reserve.data && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>{t('tarificacion.reserveTitle')}</h3>
          <FormulaBlock
            latex="{}_tV = SA \\cdot A_{x+t} - P \\cdot \\ddot{a}_{x+t}"
            label={t('tarificacion.reserveFormula')}
          />
          <LineChart
            traces={[{
              x: reserve.data.trajectory.map(p => p.duration),
              y: reserve.data.trajectory.map(p => p.reserve),
              name: 'Reserva',
              color: '#C41E3A',
            }]}
            xTitle="Duración (años)"
            yTitle="Reserva ($)"
            height={350}
          />
        </div>
      )}

      {sensitivity.data && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>{t('tarificacion.sensitivityTitle')}</h3>
          <LineChart
            traces={[{
              x: sensitivity.data.results.map(r => `${(r.interest_rate * 100).toFixed(0)}%`),
              y: sensitivity.data.results.map(r => r.annual_premium),
              name: 'Prima anual',
              color: '#C41E3A',
            }]}
            xTitle="Tasa de interés"
            yTitle="Prima anual ($)"
            height={350}
          />
        </div>
      )}
    </PageLayout>
  );
}
