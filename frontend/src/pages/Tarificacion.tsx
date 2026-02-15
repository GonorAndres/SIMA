import { useState, useMemo } from 'react';
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

const formulaSrcMap: Record<string, string> = {
  whole_life: '/formulas/whole_life_premium.png',
  term: '/formulas/term_premium.png',
  endowment: '/formulas/endowment_premium.png',
};

const formulaAltMap: Record<string, string> = {
  whole_life: 'P = SA * M_x / N_x',
  term: 'P = SA * (M_x - M_{x+n}) / (N_x - N_{x+n})',
  endowment: 'P = SA * (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})',
};

export default function Tarificacion() {
  const { t } = useTranslation();
  const premium = usePost<PremiumFormData, PremiumResponse>('/pricing/premium');
  const reserve = usePost<PremiumFormData, ReserveResponse>('/pricing/reserve');
  const sensitivity = usePost<object, SensitivityResponse>('/pricing/sensitivity');
  const [lastRequest, setLastRequest] = useState<PremiumFormData | null>(null);

  const productLabels: Record<string, string> = useMemo(() => ({
    whole_life: t('forms.wholeLife'),
    term: t('forms.termLife'),
    endowment: t('forms.endowment'),
  }), [t]);

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
      <div className={styles.splitLayout} data-demo-section="top">
        <div>
          <h3 className={styles.sectionTitle}>{t('tarificacion.calcTitle')}</h3>
          <PremiumForm onSubmit={handleSubmit} loading={loading} />
        </div>

        <div>
          {premium.loading && <LoadingState />}
          {premium.error && <p className={styles.errorText}>Error: {premium.error}</p>}

          {premium.data && (
            <div className={styles.resultPanel}>
              <div className={styles.productLabel}>
                {productLabels[premium.data.product_type] ?? premium.data.product_type}
                {` -- ${t('tarificacion.ageLabel')} `}{premium.data.age}
              </div>
              <MetricBlock
                label={t('tarificacion.annualPremium')}
                value={`$${premium.data.annual_premium.toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
              />
              <MetricBlock
                label={t('tarificacion.premiumRate')}
                value={`${(premium.data.premium_rate * 100).toFixed(4)}%`}
              />

              {lastRequest && formulaSrcMap[lastRequest.product_type] && (
                <FormulaBlock
                  src={formulaSrcMap[lastRequest.product_type]}
                  alt={formulaAltMap[lastRequest.product_type]}
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
            src="/formulas/prospective_reserve.png"
            alt="tV = SA * A_{x+t} - P * a-double-dot_{x+t}"
            label={t('tarificacion.reserveFormula')}
            description="tV = reserve at time t, A = insurance actuarial value, a-double-dot = annuity-due, P = net premium"
          />
          <LineChart
            traces={[{
              x: reserve.data.trajectory.map(p => p.duration),
              y: reserve.data.trajectory.map(p => p.reserve),
              name: t('tarificacion.reserve'),
              color: '#C41E3A',
            }]}
            xTitle={t('tarificacion.durationYears')}
            yTitle={t('tarificacion.reserveAmount')}
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
              name: t('tarificacion.annualPremiumChart'),
              color: '#C41E3A',
            }]}
            xTitle={t('tarificacion.interestRateAxis')}
            yTitle={t('tarificacion.annualPremiumAxis')}
            height={350}
          />
        </div>
      )}
    </PageLayout>
  );
}
