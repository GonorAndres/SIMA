import { useEffect, useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import Section from '../components/layout/Section';
import SectionRail from '../components/layout/SectionRail';
import type { RailItem } from '../components/layout/SectionRail';
import MetricBlock from '../components/data/MetricBlock';
import DataTable from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import PolicyForm from '../components/forms/PolicyForm';
import type { PolicyData } from '../components/forms/PolicyForm';
import WaterfallChart from '../components/charts/WaterfallChart';
import SolvencyGauge from '../components/charts/SolvencyGauge';
import FormulaBlock from '../components/data/FormulaBlock';
import InsightCard from '../components/data/InsightCard';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import { usePost, useGet } from '../hooks/useApi';
import type { SCRResponse, PortfolioSummaryResponse, PortfolioBELResponse, LISFComplianceResponse } from '../types';
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
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'es' ? 'es' : 'en';
  const portfolio = useGet<PortfolioSummaryResponse>('/portfolio/summary');
  const bel = usePost<object, PortfolioBELResponse>('/portfolio/bel');
  const scr = usePost<object, SCRResponse>('/scr/compute');
  const compliance = useGet<LISFComplianceResponse>('/scr/compliance');
  const [computed, setComputed] = useState(false);
  const [showPolicyForm, setShowPolicyForm] = useState(false);
  const [addingPolicy, setAddingPolicy] = useState(false);

  const policyColumns = useMemo(() => getPolicyColumns(t), [t]);
  const belColumns = useMemo(() => getBelColumns(t), [t]);

  const portfolioExecute = portfolio.execute;
  const complianceExecute = compliance.execute;

  useEffect(() => {
    portfolioExecute();
    complianceExecute();
  }, [portfolioExecute, complianceExecute]);

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

  // Helper to get description in current language
  const desc = (m: { description_es: string; description_en: string }) =>
    lang === 'es' ? m.description_es : m.description_en;

  const railItems: RailItem[] = useMemo(() => [
    { id: 'sec-marco', step: '1', label: t('scr.railFramework') },
    { id: 'sec-portafolio', step: '2', label: t('scr.railPortfolio') },
    { id: 'sec-bel', step: '3', label: t('scr.railBel') },
    { id: 'sec-modulos', step: '4', label: t('scr.railModules') },
    { id: 'sec-agregacion', step: '5', label: t('scr.railAggregation') },
    { id: 'sec-limitaciones', step: '6', label: t('scr.railLimitations') },
  ], [t]);

  return (
    <PageLayout
      title={t('scr.title')}
      subtitle={t('scr.subtitle')}
      rail={<SectionRail items={railItems} />}
    >
      {/* LISF Regulatory Context */}
      {/* Toda la seccion regulatoria cuelga de compliance.data: si la peticion
          falla, el paso 1 del recorrido desaparece sin dejar rastro. */}
      {compliance.error && !compliance.loading && (
        <ErrorState message={compliance.error} onRetry={() => complianceExecute()} />
      )}
      {compliance.data && (
        <Section
          step="1"
          id="sec-marco"
          title={t('scr.regulatorySectionTitle')}
          explainer={t('scr.regulatoryExplainer')}
        >
          <InsightCard variant="regulatory" title={t('scr.whatIsScrTitle')}>
            <p>{lang === 'es' ? compliance.data.framework_description_es : compliance.data.framework_description_en}</p>
          </InsightCard>

          <div className={styles.regulatoryGrid}>
            {compliance.data.risk_modules.map((m) => (
              <div key={m.module} className={styles.regulatoryModule}>
                <div className={styles.moduleHeader}>
                  <span className={styles.moduleName}>{t(`scr.${m.module === 'interest_rate' ? 'interestRate' : m.module}`)}</span>
                  <span className={styles.moduleShock}>{m.standard_shock}</span>
                </div>
                <p className={styles.moduleDesc}>{desc(m)}</p>
                <div className={styles.moduleRef}>{m.lisf_reference}</div>
              </div>
            ))}
          </div>

          <InsightCard variant="insight" title={t('scr.diversificationInsight')}>
            <p>{lang === 'es' ? compliance.data.correlation_basis_es : compliance.data.correlation_basis_en}</p>
          </InsightCard>
        </Section>
      )}

      <Section
        step="2"
        id="sec-portafolio"
        title={t('scr.portfolio')}
        explainer={t('scr.portfolioExplainer')}
        demoSection="top"
        actions={
          <div className={styles.btnRow}>
            <button
              className={styles.addPolicyToggle}
              onClick={() => setShowPolicyForm(!showPolicyForm)}
              aria-expanded={showPolicyForm}
            >
              {showPolicyForm ? t('scr.close') : t('scr.addPolicy')}
            </button>
            <button className={styles.resetBtn} onClick={handleReset}>
              {t('scr.reset')}
            </button>
          </div>
        }
      >
        <FormulaBlock
          src="/formulas/scr_aggregation.png"
          alt="SCR = sqrt(S^T * C * S)"
          label={t('scr.aggFormula')}
          description="S = vector of individual SCR modules, C = correlation matrix capturing risk dependencies"
        />

        {showPolicyForm && (
          <div className={styles.policyFormWrapper}>
            <PolicyForm onSubmit={handleAddPolicy} loading={addingPolicy} />
          </div>
        )}

        {portfolio.loading && <LoadingState message={t('scr.loadingPortfolio')} />}
        {portfolio.error && !portfolio.loading && (
          <ErrorState message={portfolio.error} onRetry={() => portfolioExecute()} />
        )}
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
      </Section>

      {/* Compute SCR button */}
      {!computed && (
        <div className={styles.computeCenter}>
          <p className={styles.computeHint}>{t('scr.computeHint')}</p>
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
      {(scr.error || bel.error) && !scr.loading && (
        <ErrorState message={scr.error ?? bel.error ?? undefined} onRetry={handleCompute} />
      )}

      {scr.data && (
        <>
          {/* BEL Metrics */}
          <Section
            step="3"
            id="sec-bel"
            title={t('scr.belTitle')}
            explainer={t('scr.belExplainer')}
          >
            <InsightCard variant="info" title={t('scr.belExplainTitle')}>
              <p>{t('scr.belExplain')}</p>
            </InsightCard>
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
          </Section>

          {/* Risk Modules */}
          <Section
            step="4"
            id="sec-modulos"
            title={t('scr.riskModules')}
            explainer={t('scr.riskModulesExplainer')}
          >

            {/* Per-module insights */}
            {compliance.data && (
              <div className={styles.moduleInsights}>
                {compliance.data.risk_modules.map((m) => {
                  const scrVal = m.module === 'mortality' ? scr.data!.mortality.scr
                    : m.module === 'longevity' ? scr.data!.longevity.scr
                    : m.module === 'interest_rate' ? scr.data!.interest_rate.scr
                    : scr.data!.catastrophe.scr;
                  const pct = scr.data!.total_aggregation.scr_aggregated > 0
                    ? (scrVal / scr.data!.total_aggregation.scr_aggregated * 100).toFixed(1)
                    : '0';
                  return (
                    <InsightCard key={m.module} variant="info">
                      <strong>{t(`scr.${m.module === 'interest_rate' ? 'interestRate' : m.module}`)}</strong>
                      {' '}{fmt(scrVal)} ({pct}% {t('scr.ofTotal')})
                      {' -- '}{desc(m)}
                    </InsightCard>
                  );
                })}
              </div>
            )}

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
          </Section>

          {/* Aggregation & Solvency */}
          <Section
            step="5"
            id="sec-agregacion"
            title={t('scr.aggSolvency')}
            explainer={t('scr.aggExplainer')}
          >

            <InsightCard variant="insight" title={t('scr.diversificationInsight')}>
              <p>{t('scr.diversificationExplain')}</p>
            </InsightCard>

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

            {/* Risk margin explanation */}
            {compliance.data && (
              <InsightCard variant="regulatory" title={t('scr.riskMarginExplainTitle')}>
                <p>{lang === 'es' ? compliance.data.risk_margin_basis_es : compliance.data.risk_margin_basis_en}</p>
              </InsightCard>
            )}
          </Section>

          {/* Limitations disclosure */}
          {compliance.data && (
            <Section
              step="6"
              id="sec-limitaciones"
              title={t('scr.coverageLimitations')}
              explainer={t('scr.coverageExplainer')}
            >
              <div className={styles.twoCol}>
                <div>
                  <h4 className={styles.belSubheading}>{t('scr.coverageTitle')}</h4>
                  <ul className={styles.complianceList}>
                    {compliance.data.coverage.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
                <div>
                  <h4 className={styles.belSubheading}>{t('scr.limitationsTitle')}</h4>
                  <ul className={styles.complianceList}>
                    {compliance.data.limitations.map((l, i) => <li key={i}>{l}</li>)}
                  </ul>
                </div>
              </div>
            </Section>
          )}
        </>
      )}
    </PageLayout>
  );
}
