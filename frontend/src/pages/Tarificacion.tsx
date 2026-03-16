import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import PremiumForm from '../components/forms/PremiumForm';
import type { PremiumRequest as PremiumFormData } from '../components/forms/PremiumForm';
import MetricBlock from '../components/data/MetricBlock';
import FormulaBlock from '../components/data/FormulaBlock';
import InsightCard from '../components/data/InsightCard';
import DataTable from '../components/data/DataTable';
import LineChart from '../components/charts/LineChart';
import Plot from '../components/charts/Plot';
import { defaultLayout, defaultConfig } from '../components/charts/chartDefaults';
import LoadingState from '../components/common/LoadingState';
import { usePost } from '../hooks/useApi';
import type { PremiumResponse, ReserveResponse, SensitivityResponse, CrossCountryPremiumResponse } from '../types';
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
  const crossCountry = usePost<PremiumFormData, CrossCountryPremiumResponse>('/pricing/cross-country');
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
    crossCountry.execute(req);
  };

  const loading = premium.loading || reserve.loading || sensitivity.loading || crossCountry.loading;

  const countryColors: Record<string, string> = {
    'Mexico': '#C41E3A',
    'Estados Unidos': '#1A365D',
    'España': '#D4A843',
  };

  const crossCountryColumns = [
    { key: 'country', label: t('tarificacion.crossCountryCountry') },
    { key: 'annual_premium', label: t('tarificacion.crossCountryPremium'), align: 'right' as const, numeric: true, format: (v: unknown) => `$${(v as number).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { key: 'premium_rate', label: t('tarificacion.crossCountryRate'), align: 'right' as const, numeric: true, format: (v: unknown) => `${((v as number) * 100).toFixed(4)}%` },
    { key: 'drift', label: t('tarificacion.crossCountryDrift'), align: 'right' as const, numeric: true, format: (v: unknown) => (v as number).toFixed(4) },
    { key: 'explained_var', label: t('tarificacion.crossCountryVar'), align: 'right' as const, numeric: true, format: (v: unknown) => `${((v as number) * 100).toFixed(1)}%` },
  ];

  return (
    <PageLayout
      title={t('tarificacion.title')}
      subtitle={t('tarificacion.subtitle')}
    >
      <InsightCard variant="insight" title={t('tarificacion.equivalenceTitle')}>
        <p>{t('tarificacion.equivalenceExplain')}</p>
      </InsightCard>

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
          <InsightCard variant="info" title={t('tarificacion.reserveInsightTitle')}>
            <p>{t('tarificacion.reserveInsight')}</p>
          </InsightCard>
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
          <InsightCard variant="warning" title={t('tarificacion.sensitivityInsightTitle')}>
            <p>{t('tarificacion.sensitivityInsight')}</p>
          </InsightCard>
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

      {crossCountry.data && (() => {
        const entries = crossCountry.data.entries;
        const mxPremium = entries[0]?.annual_premium ?? 1;
        const pctDiff = (e: typeof entries[0]) =>
          ((e.annual_premium - mxPremium) / mxPremium * 100).toFixed(0);

        return (
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>{t('tarificacion.crossCountryTitle')}</h3>
            <InsightCard variant="insight" title={t('tarificacion.crossCountryInsightTitle')}>
              <p>{t('tarificacion.crossCountryInsight')}</p>
              {entries.length >= 3 && (
                <p style={{ marginTop: 8, fontWeight: 500 }}>
                  {t('tarificacion.crossCountryDynamic', {
                    mxPremium: `$${mxPremium.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                    usaPct: pctDiff(entries[1]),
                    spainPct: pctDiff(entries[2]),
                  })}
                </p>
              )}
            </InsightCard>

            <div className={styles.metricsRow}>
              {entries.map(e => (
                <MetricBlock
                  key={e.country}
                  label={e.country}
                  value={`$${e.annual_premium.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                  unit={e.country === 'Mexico'
                    ? `drift ${e.drift.toFixed(2)}`
                    : `${pctDiff(e)}% vs MX`}
                />
              ))}
            </div>

            <Plot
              data={[{
                x: entries.map(e => e.country),
                y: entries.map(e => e.annual_premium),
                type: 'bar' as const,
                marker: { color: entries.map(e => countryColors[e.country] || '#666') },
                text: entries.map(e => `$${e.annual_premium.toLocaleString(undefined, { maximumFractionDigits: 0 })}`),
                textposition: 'outside' as const,
                hovertemplate: '%{x}<br>$%{y:,.0f}<extra></extra>',
              }]}
              layout={{
                ...defaultLayout,
                height: 350,
                showlegend: false,
                yaxis: {
                  ...defaultLayout.yaxis,
                  title: { text: t('tarificacion.annualPremiumAxis') },
                  rangemode: 'tozero' as const,
                },
                bargap: 0.4,
              }}
              config={defaultConfig}
              style={{ width: '100%' }}
            />
            <DataTable columns={crossCountryColumns} data={crossCountry.data.entries as unknown as Record<string, unknown>[]} sortable={false} />
          </div>
        );
      })()}
    </PageLayout>
  );
}
