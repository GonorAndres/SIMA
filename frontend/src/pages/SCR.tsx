import { useEffect, useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import MetricBlock from '../components/data/MetricBlock';
import DataTable from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import PolicyForm from '../components/forms/PolicyForm';
import type { PolicyData } from '../components/forms/PolicyForm';
import WaterfallChart from '../components/charts/WaterfallChart';
import SolvencyGauge from '../components/charts/SolvencyGauge';
import FormulaBlock from '../components/data/FormulaBlock';
import LoadingState from '../components/common/LoadingState';
import { usePost, useGet } from '../hooks/useApi';
import type { SCRResponse, PortfolioSummaryResponse, PortfolioBELResponse } from '../types';
import api from '../api/client';
import styles from './SCR.module.css';

const fmt = (v: number) => `$${(v / 1000).toFixed(1)}K`;

function getPolicyColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'policy_id', label: t('tables.policyId'), align: 'left' },
    { key: 'product_type', label: t('tables.product'), align: 'left' },
    { key: 'issue_age', label: t('tables.issueAge'), align: 'right', numeric: true },
    { key: 'attained_age', label: t('tables.attainedAge'), align: 'right', numeric: true },
    { key: 'sum_assured', label: t('tables.sumAssured'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString()}` },
    { key: 'annual_pension', label: t('tables.annualPension'), align: 'right', numeric: true, format: (v) => Number(v) > 0 ? `$${Number(v).toLocaleString()}` : '-' },
    { key: 'duration', label: t('tables.duration'), align: 'right', numeric: true },
  ];
}

function getBelColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'policy_id', label: t('tables.policyId'), align: 'left' },
    { key: 'product_type', label: t('tables.product'), align: 'left' },
    { key: 'attained_age', label: t('tables.age'), align: 'right', numeric: true },
    { key: 'bel', label: t('tables.bel'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
  ];
}

export default function SCR() {
  const { t } = useTranslation();
  const portfolio = useGet<PortfolioSummaryResponse>('/portfolio/summary');
  const bel = usePost<object, PortfolioBELResponse>('/portfolio/bel');
  const scr = usePost<object, SCRResponse>('/scr/compute');
  const [computed, setComputed] = useState(false);
  const [showPolicyForm, setShowPolicyForm] = useState(false);
  const [addingPolicy, setAddingPolicy] = useState(false);

  const policyColumns = useMemo(() => getPolicyColumns(t), [t]);
  const belColumns = useMemo(() => getBelColumns(t), [t]);

  const portfolioExecute = portfolio.execute;

  useEffect(() => {
    portfolioExecute();
  }, [portfolioExecute]);

  const handleCompute = async () => {
    await Promise.all([
      scr.execute({ available_capital: 1_000_000 }),
      bel.execute({ interest_rate: 0.05 }),
    ]);
    setComputed(true);
  };

  const handleAddPolicy = useCallback(async (policy: PolicyData) => {
    setAddingPolicy(true);
    try {
      await api.post('/portfolio/policy', policy);
      await portfolioExecute();
      setShowPolicyForm(false);
      setComputed(false);
    } finally {
      setAddingPolicy(false);
    }
  }, [portfolioExecute]);

  const handleReset = useCallback(async () => {
    await api.post('/portfolio/reset');
    await portfolioExecute();
    setComputed(false);
  }, [portfolioExecute]);

  return (
    <PageLayout
      title={t('scr.title')}
      subtitle={t('scr.subtitle')}
    >
      <FormulaBlock
        latex="SCR = \\sqrt{\\vec{S}^T \\cdot C \\cdot \\vec{S}}"
        label={t('scr.aggFormula')}
      />

      {/* Portfolio section */}
      <div className={styles.section}>
        <div className={styles.portfolioHeader}>
          <h3 className={styles.sectionTitle}>{t('scr.portfolio')}</h3>
          <div className={styles.btnRow}>
            <button
              className={styles.addPolicyToggle}
              onClick={() => setShowPolicyForm(!showPolicyForm)}
            >
              {showPolicyForm ? 'X' : t('scr.addPolicy')}
            </button>
            <button className={styles.resetBtn} onClick={handleReset}>
              {t('scr.reset')}
            </button>
          </div>
        </div>

        {showPolicyForm && (
          <div className={styles.policyFormWrapper}>
            <PolicyForm onSubmit={handleAddPolicy} loading={addingPolicy} />
          </div>
        )}

        {portfolio.loading && <LoadingState message={t('scr.loadingPortfolio')} />}
        {portfolio.data && (
          <>
            <div className={styles.metricsRow}>
              <MetricBlock label={t('scr.policies')} value={portfolio.data.n_policies} />
              <MetricBlock label={t('scr.death')} value={portfolio.data.n_death} />
              <MetricBlock label={t('scr.annuities')} value={portfolio.data.n_annuity} />
              <MetricBlock
                label={t('scr.totalSA')}
                value={`$${(portfolio.data.total_sum_assured / 1e6).toFixed(2)}M`}
              />
            </div>
            <DataTable
              columns={policyColumns}
              data={portfolio.data.policies as unknown as Record<string, unknown>[]}
            />
          </>
        )}
      </div>

      {/* Compute SCR button */}
      {!computed && (
        <div className={styles.computeCenter}>
          <button
            onClick={handleCompute}
            disabled={scr.loading}
            className={styles.computeBtn}
          >
            {scr.loading ? t('scr.computing') : t('scr.compute')}
          </button>
        </div>
      )}

      {scr.loading && <LoadingState message={t('scr.running')} />}
      {scr.error && <p className={styles.errorText}>Error: {scr.error}</p>}

      {scr.data && (
        <>
          {/* BEL Metrics */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>{t('scr.belTitle')}</h3>
            <div className={styles.metricsRow}>
              <MetricBlock label={t('scr.belTotal')} value={`$${(scr.data.bel_base / 1e6).toFixed(2)}M`} />
              <MetricBlock label={t('scr.belDeath')} value={`$${(scr.data.bel_death / 1e3).toFixed(0)}K`} />
              <MetricBlock label={t('scr.belAnnuity')} value={`$${(scr.data.bel_annuity / 1e6).toFixed(2)}M`} />
            </div>

            {/* BEL breakdown table */}
            {bel.data && (
              <>
                <h4 className={styles.belSubheading}>
                  {t('scr.belBreakdown')}
                </h4>
                <DataTable
                  columns={belColumns}
                  data={bel.data.breakdown as unknown as Record<string, unknown>[]}
                />
              </>
            )}
          </div>

          {/* Risk Modules */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>{t('scr.riskModules')}</h3>
            <div className={styles.metricsRow}>
              <MetricBlock label={t('scr.scrMort')} value={fmt(scr.data.mortality.scr)} />
              <MetricBlock label={t('scr.scrLong')} value={fmt(scr.data.longevity.scr)} />
              <MetricBlock label={t('scr.scrIR')} value={fmt(scr.data.interest_rate.scr)} />
              <MetricBlock label={t('scr.scrCat')} value={fmt(scr.data.catastrophe.scr)} />
            </div>

            <WaterfallChart
              categories={[
                t('scr.mortality'),
                t('scr.longevity'),
                t('scr.interestRate'),
                t('scr.catastrophe'),
                t('scr.diversification'),
                t('scr.totalScr'),
              ]}
              values={[
                scr.data.mortality.scr,
                scr.data.longevity.scr,
                scr.data.interest_rate.scr,
                scr.data.catastrophe.scr,
                -scr.data.total_aggregation.diversification_benefit,
                scr.data.total_aggregation.scr_aggregated,
              ]}
              title={t('scr.decomposition')}
              height={400}
            />
          </div>

          {/* Aggregation & Solvency */}
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>{t('scr.aggSolvency')}</h3>
            <div className={styles.splitLayout}>
              <div>
                <MetricBlock
                  label={t('scr.diversification')}
                  value={`${(scr.data.total_aggregation.diversification_pct ?? 0).toFixed(1)}%`}
                />
                <MetricBlock label={t('scr.riskMargin')} value={fmt(scr.data.risk_margin.risk_margin)} />
                <MetricBlock
                  label={t('scr.techProvisions')}
                  value={`$${(scr.data.technical_provisions / 1e6).toFixed(2)}M`}
                />
                <MetricBlock label={t('scr.scrTotal')} value={fmt(scr.data.total_aggregation.scr_aggregated)} />
              </div>
              <div>
                {scr.data.solvency && (
                  <SolvencyGauge ratio={scr.data.solvency.ratio} />
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </PageLayout>
  );
}
