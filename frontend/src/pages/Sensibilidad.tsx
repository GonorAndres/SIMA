import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useDemo } from '../context/DemoContext';
import PageLayout from '../components/layout/PageLayout';
import SliderInput from '../components/forms/SliderInput';
import MetricBlock from '../components/data/MetricBlock';
import LineChart from '../components/charts/LineChart';
import HeatmapChart from '../components/charts/HeatmapChart';
import DataTable from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import LoadingState from '../components/common/LoadingState';
import { usePost, useGet } from '../hooks/useApi';
import api from '../api/client';
import type {
  SensitivityResponse,
  MortalityShockRequest,
  MortalityShockResponse,
  CrossCountryResponse,
  CovidComparisonResponse,
} from '../types';
import styles from './Sensibilidad.module.css';

type TabKey = 'interest_rate' | 'mortality' | 'comparison' | 'covid';

const rates = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08];
const COUNTRY_COLORS = ['#C41E3A', '#424242', '#9E9E9E', '#1E88E5', '#43A047', '#E65100'];
const heatmapAges = [20, 30, 40, 50, 60];

function getSensColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'interest_rate', label: t('tables.interestRate'), align: 'right', numeric: true, format: (v) => `${(Number(v) * 100).toFixed(0)}%` },
    { key: 'annual_premium', label: t('tables.annualPremium'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}` },
  ];
}

function getCrossColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'country', label: t('tables.country'), align: 'left' },
    { key: 'drift', label: t('tables.drift'), align: 'right', numeric: true },
    { key: 'explained_var', label: t('tables.explainedVar'), align: 'right' },
    { key: 'q60', label: t('tables.qx60'), align: 'right', numeric: true },
    { key: 'premium_age40', label: t('tables.premiumAge40'), align: 'right' },
  ];
}

function getCovidColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'age', label: t('tables.age'), align: 'right', numeric: true },
    { key: 'pre_covid', label: t('tables.preCovid'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString()}` },
    { key: 'full', label: t('tables.fullPeriod'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString()}` },
    { key: 'pct_change', label: t('tables.premiumChange'), align: 'right', numeric: true, format: (v) => `+${Number(v).toFixed(2)}%` },
  ];
}

export default function Sensibilidad() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabKey>('interest_rate');
  const [age, setAge] = useState(40);
  const [sumAssured, setSumAssured] = useState(1000000);

  const sensColumns = useMemo(() => getSensColumns(t), [t]);
  const crossColumns = useMemo(() => getCrossColumns(t), [t]);
  const covidColumns = useMemo(() => getCovidColumns(t), [t]);

  // Tab 1: Interest rate analysis
  const wl = usePost<object, SensitivityResponse>('/pricing/sensitivity');
  const term = usePost<object, SensitivityResponse>('/pricing/sensitivity');
  const endow = usePost<object, SensitivityResponse>('/pricing/sensitivity');

  // Heatmap: one request per age
  const [heatmapData, setHeatmapData] = useState<number[][] | null>(null);
  const [heatmapLoading, setHeatmapLoading] = useState(false);

  // Tab 2: Dynamic mortality shock
  const shockApi = usePost<MortalityShockRequest, MortalityShockResponse>('/sensitivity/mortality-shock');
  const [shockAge, setShockAge] = useState(40);
  const [shockProduct, setShockProduct] = useState('whole_life');

  // Tab 3: Cross-country from API
  const crossCountry = useGet<CrossCountryResponse>('/sensitivity/cross-country');

  // Tab 4: COVID comparison from API
  const covid = useGet<CovidComparisonResponse>('/sensitivity/covid-comparison');

  const crossExecute = crossCountry.execute;
  const covidExecute = covid.execute;
  useEffect(() => {
    crossExecute();
    covidExecute();
  }, [crossExecute, covidExecute]);

  // Auto-switch tabs when demo mode navigates to a section
  const demo = useDemo();
  useEffect(() => {
    if (!demo?.active) return;
    const key = demo.narrativeKey;
    if (key === 'demo.step9') setActiveTab('interest_rate');
    else if (key === 'demo.step10') setActiveTab('comparison');
    else if (key === 'demo.step11') setActiveTab('covid');
  }, [demo?.active, demo?.narrativeKey]);

  const handleRunInterestRate = async () => {
    // Run line chart analysis
    wl.execute({ product_type: 'whole_life', age, sum_assured: sumAssured, rates });
    term.execute({ product_type: 'term', age, sum_assured: sumAssured, term: 20, rates });
    endow.execute({ product_type: 'endowment', age, sum_assured: sumAssured, term: 20, rates });

    // Run heatmap: for each age, get premiums at all rates
    setHeatmapLoading(true);
    try {
      const results = await Promise.all(
        heatmapAges.map(async (hAge) => {
          const res = await api.post('/pricing/sensitivity', {
            product_type: 'whole_life',
            age: hAge,
            sum_assured: sumAssured,
            rates,
          });
          return (res.data as SensitivityResponse).results.map((r) => r.annual_premium);
        })
      );
      setHeatmapData(results);
    } finally {
      setHeatmapLoading(false);
    }
  };

  const loading = wl.loading || term.loading || endow.loading || heatmapLoading;

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'interest_rate', label: t('sensibilidad.tabInterest') },
    { key: 'mortality', label: t('sensibilidad.tabMortality') },
    { key: 'comparison', label: t('sensibilidad.tabComparison') },
    { key: 'covid', label: t('sensibilidad.tabCovid') },
  ];

  return (
    <PageLayout
      title={t('sensibilidad.title')}
      subtitle={t('sensibilidad.subtitle')}
    >
      {/* Tabs */}
      <div className={styles.tabRow}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`${styles.tab} ${activeTab === tab.key ? styles.tabActive : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Interest Rate */}
      {activeTab === 'interest_rate' && (
        <div data-demo-section="interest">
          <h3 className={styles.sectionTitle}>{t('sensibilidad.interestHeader')}</h3>
          <p className={styles.narrative}>
            {t('sensibilidad.interestIntro')}
          </p>
          <div className={styles.controls}>
            <SliderInput label={t('sensibilidad.age')} min={20} max={70} step={1} value={age} onChange={setAge} unit={t('forms.years')} />
            <div className={styles.fieldGroup}>
              <label className={styles.fieldLabel}>{t('sensibilidad.sumAssured')}</label>
              <input
                type="number"
                className={styles.numberInput}
                value={sumAssured}
                onChange={(e) => setSumAssured(Number(e.target.value))}
                min={100000}
                step={100000}
              />
            </div>
            <button
              onClick={handleRunInterestRate}
              disabled={loading}
              className={styles.runBtn}
            >
              {loading ? t('sensibilidad.computing') : t('sensibilidad.runAnalysis')}
            </button>
          </div>

          {loading && <LoadingState />}

          {wl.data && term.data && endow.data && (
            <>
              <LineChart
                traces={[
                  {
                    x: wl.data.results.map(r => `${(r.interest_rate * 100).toFixed(0)}%`),
                    y: wl.data.results.map(r => r.annual_premium),
                    name: t('sensibilidad.wholeLife'),
                    color: '#C41E3A',
                  },
                  {
                    x: term.data.results.map(r => `${(r.interest_rate * 100).toFixed(0)}%`),
                    y: term.data.results.map(r => r.annual_premium),
                    name: `${t('sensibilidad.term')} (20)`,
                    color: '#424242',
                  },
                  {
                    x: endow.data.results.map(r => `${(r.interest_rate * 100).toFixed(0)}%`),
                    y: endow.data.results.map(r => r.annual_premium),
                    name: `${t('sensibilidad.endowment')} (20)`,
                    color: '#9E9E9E',
                  },
                ]}
                title={t('sensibilidad.premiumVsRate')}
                xTitle={t('tarificacion.interestRateAxis')}
                yTitle={t('tarificacion.annualPremiumAxis')}
                height={400}
              />

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.wholeLife')}</h3>
                <DataTable
                  columns={sensColumns}
                  data={wl.data.results as unknown as Record<string, unknown>[]}
                />
              </div>
            </>
          )}

          {/* Heatmap */}
          {heatmapData && (
            <div className={styles.section}>
              <HeatmapChart
                x={rates.map(r => `${(r * 100).toFixed(0)}%`)}
                y={heatmapAges.map(a => `${a}`)}
                z={heatmapData}
                title={t('tarificacion.heatmapTitle')}
                xTitle={t('tarificacion.interestRateAxis')}
                yTitle={t('charts.age')}
                height={350}
              />
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Mortality Shock */}
      {activeTab === 'mortality' && (
        <div>
          <h3 className={styles.sectionTitle}>{t('sensibilidad.shockHeader')}</h3>
          <p className={styles.narrative}>
            {t('sensibilidad.shockIntro')}
          </p>
          <div className={styles.controls}>
            <SliderInput label={t('sensibilidad.age')} min={20} max={70} step={1} value={shockAge} onChange={setShockAge} unit={t('forms.years')} />
            <div className={styles.fieldGroup}>
              <label className={styles.fieldLabel}>{t('sensibilidad.productType')}</label>
              <select
                className={styles.numberInput}
                value={shockProduct}
                onChange={(e) => setShockProduct(e.target.value)}
              >
                <option value="whole_life">{t('sensibilidad.wholeLife')}</option>
                <option value="term">{t('sensibilidad.term')}</option>
                <option value="endowment">{t('sensibilidad.endowment')}</option>
              </select>
            </div>
            <button
              onClick={() => shockApi.execute({ age: shockAge, sum_assured: sumAssured, product_type: shockProduct, factors: [-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30] })}
              disabled={shockApi.loading}
              className={styles.runBtn}
            >
              {shockApi.loading ? t('sensibilidad.computing') : t('sensibilidad.runAnalysis')}
            </button>
          </div>

          {shockApi.loading && <LoadingState message={t('sensibilidad.loadingShock')} />}

          {shockApi.data && (
            <>
              <div className={styles.comparisonGrid}>
                <MetricBlock label={t('sensibilidad.wholeLife')} value={`$${shockApi.data.base_premium.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} unit={`${t('tarificacion.ageLabel')} ${shockApi.data.age}`} />
                <MetricBlock label="+30% q_x" value={`+${shockApi.data.pct_changes[shockApi.data.pct_changes.length - 1]?.toFixed(1)}%`} unit={t('tables.premium')} />
                <MetricBlock label="-30% q_x" value={`${shockApi.data.pct_changes[0]?.toFixed(1)}%`} unit={t('tables.premium')} />
              </div>

              <LineChart
                traces={[{
                  x: shockApi.data.factors.map(f => `${(f * 100).toFixed(0)}%`),
                  y: shockApi.data.premiums,
                  name: `${t('sensibilidad.' + shockProduct)} (${t('tarificacion.ageLabel')} ${shockAge})`,
                  color: '#C41E3A',
                }]}
                title={t('sensibilidad.premiumVsShock')}
                xTitle={t('tarificacion.shockAxis')}
                yTitle={t('tarificacion.annualPremiumAxis')}
                height={350}
              />

              <p className={styles.narrative} style={{ fontStyle: 'italic' }}>
                {t('sensibilidad.asymmetryNote')}
              </p>
            </>
          )}
        </div>
      )}

      {/* Tab 3: Cross-Country Comparison */}
      {activeTab === 'comparison' && (
        <div data-demo-section="cross-country">
          <h3 className={styles.sectionTitle}>{t('sensibilidad.crossHeader')}</h3>
          <p className={styles.narrative}>
            {t('sensibilidad.crossIntro')}
          </p>

          {crossCountry.loading && <LoadingState message={t('sensibilidad.loadingCrossCountry')} />}

          {crossCountry.data && (
            <>
              <div className={styles.comparisonGrid}>
                {crossCountry.data.countries.map(c => (
                  <MetricBlock key={c.country} label={`${t('tables.drift')} ${c.country}`} value={c.drift.toFixed(3)} unit={t('inicio.yearUnit')} />
                ))}
              </div>

              <DataTable
                columns={crossColumns}
                data={crossCountry.data.countries.map(c => ({
                  country: c.country,
                  drift: c.drift,
                  explained_var: `${(c.explained_var * 100).toFixed(1)}%`,
                  q60: c.q60.toFixed(4),
                  premium_age40: `$${c.premium_age40.toLocaleString()}`,
                })) as unknown as Record<string, unknown>[]}
              />

              {/* k_t overlay */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.ktOverlay')}</h3>
                <LineChart
                  traces={crossCountry.data.kt_profiles.map((p, i) => ({
                    x: p.years,
                    y: p.kt,
                    name: p.country,
                    color: COUNTRY_COLORS[i % COUNTRY_COLORS.length],
                  }))}
                  xTitle={t('charts.year')}
                  yTitle="k_t"
                  height={350}
                />
                <p className={styles.narrative}>{t('sensibilidad.ktCaption')}</p>
              </div>

              {/* a_x profiles */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.axProfile')}</h3>
                <LineChart
                  traces={crossCountry.data.ax_profiles.map((p, i) => ({
                    x: p.ages,
                    y: p.values,
                    name: p.country,
                    color: COUNTRY_COLORS[i % COUNTRY_COLORS.length],
                  }))}
                  xTitle={t('charts.age')}
                  yTitle="a_x"
                  height={300}
                />
                <p className={styles.narrative}>{t('sensibilidad.axCaption')}</p>
              </div>

              {/* b_x profiles */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.bxProfile')}</h3>
                <LineChart
                  traces={crossCountry.data.bx_profiles.map((p, i) => ({
                    x: p.ages,
                    y: p.values,
                    name: p.country,
                    color: COUNTRY_COLORS[i % COUNTRY_COLORS.length],
                  }))}
                  xTitle={t('charts.age')}
                  yTitle="b_x"
                  height={300}
                />
                <p className={styles.narrative}>{t('sensibilidad.bxCaption')}</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* Tab 4: COVID Impact */}
      {activeTab === 'covid' && (
        <div data-demo-section="covid">
          <h3 className={styles.sectionTitle}>{t('sensibilidad.covidHeader')}</h3>
          <p className={styles.narrative}>
            {t('sensibilidad.covidIntro')}
          </p>

          {covid.loading && <LoadingState message={t('sensibilidad.loadingCovid')} />}

          {covid.data && (
            <>
              <div className={styles.comparisonGrid}>
                <MetricBlock label={t('sensibilidad.covidDriftPre')} value={covid.data.pre_covid.drift.toFixed(3)} unit={t('inicio.yearUnit')} />
                <MetricBlock label={t('sensibilidad.covidDriftFull')} value={covid.data.full_period.drift.toFixed(3)} unit={t('inicio.yearUnit')} />
                <MetricBlock label={t('sensibilidad.covidDriftDiff')} value={`+${(covid.data.full_period.drift - covid.data.pre_covid.drift).toFixed(3)}`} unit={t('inicio.yearUnit')} />
              </div>

              {/* k_t overlay */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.covidKtComparison')}</h3>
                <LineChart
                  traces={[
                    {
                      x: covid.data.pre_covid.years,
                      y: covid.data.pre_covid.kt,
                      name: t('sensibilidad.preCovid'),
                      color: '#424242',
                    },
                    {
                      x: covid.data.full_period.years,
                      y: covid.data.full_period.kt,
                      name: t('sensibilidad.fullPeriod'),
                      color: '#C41E3A',
                    },
                  ]}
                  xTitle={t('charts.year')}
                  yTitle="k_t"
                  height={400}
                />
              </div>

              {/* Premium impact table */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.covidPremiumImpact')}</h3>
                <DataTable
                  columns={covidColumns}
                  data={covid.data.premium_impact as unknown as Record<string, unknown>[]}
                />
              </div>
            </>
          )}
        </div>
      )}
    </PageLayout>
  );
}
