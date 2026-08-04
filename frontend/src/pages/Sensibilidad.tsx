import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useDemo } from '../context/useDemo';
import PageLayout from '../components/layout/PageLayout';
import OptionGroup from '../components/forms/OptionGroup';
import SliderInput from '../components/forms/SliderInput';
import MetricBlock from '../components/data/MetricBlock';
import LineChart from '../components/charts/LineChart';
import HeatmapChart from '../components/charts/HeatmapChart';
import DataTable from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import InsightCard from '../components/data/InsightCard';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import { usePost, useGet } from '../hooks/useApi';
import api from '../api/client';
import type {
  SensitivityResponse,
  MortalityShockRequest,
  MortalityShockResponse,
  CrossCountryResponse,
  CovidComparisonResponse,
} from '../types';
import { countryLabel, wholeMoney } from '../utils/format';
import styles from './Sensibilidad.module.css';

type TabKey = 'interest_rate' | 'mortality' | 'comparison' | 'covid';
type SexKey = 'male' | 'female' | 'unisex';

const productI18nKey: Record<string, string> = {
  whole_life: 'wholeLife',
  term: 'term',
  endowment: 'endowment',
};

const rates = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08];
const COUNTRY_COLORS = ['#C41E3A', '#424242', '#9E9E9E', '#1E88E5', '#43A047', '#E65100'];
const heatmapAges = [20, 30, 40, 50, 60];

function getSensColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'interest_rate', label: t('tables.interestRate'), align: 'right', numeric: true, format: (v) => `${(Number(v) * 100).toFixed(0)}%` },
    // Peso entero, como el resto de tablas de la pagina: los centavos de una
    // prima anual sobre un millon asegurado no informan nada.
    { key: 'annual_premium', label: t('tables.annualPremium'), align: 'right', numeric: true, format: (v) => wholeMoney(Number(v)) },
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
    // toLocaleString() sin opciones da tres decimales: las primas se muestran
    // en pesos enteros, como en el resto de la pagina.
    { key: 'pre_covid', label: t('tables.preCovid'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { key: 'full', label: t('tables.fullPeriod'), align: 'right', numeric: true, format: (v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
    { key: 'pct_change', label: t('tables.premiumChange'), align: 'right', numeric: true, format: (v) => `+${Number(v).toFixed(2)}%` },
  ];
}

export default function Sensibilidad() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabKey>('interest_rate');
  const [sex, setSex] = useState<SexKey>('male');
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

  // Tab 3: Cross-country from API. El endpoint no acepta sexo: compara los tres
  // paises en unisex por diseño, para que la comparacion tenga una sola base.
  const crossCountry = useGet<CrossCountryResponse>('/sensitivity/cross-country');

  // Las cifras de la prosa comparativa salen de esta respuesta, no de constantes.
  // El nombre del pais llega en español y con acentos que difieren entre
  // endpoints, asi que se normaliza antes de emparejar.
  const crossFigures = useMemo(() => {
    const countries = crossCountry.data?.countries;
    if (!countries) return null;
    const find = (needle: string) => countries.find((c) =>
      c.country.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().includes(needle)
    );
    const mx = find('mexico');
    const usa = find('estados unidos') ?? find('usa');
    const spain = find('espana');
    if (!mx || !usa || !spain || mx.drift === 0) return null;
    return {
      mxDrift: mx.drift.toFixed(3),
      usaDrift: usa.drift.toFixed(3),
      spainDrift: spain.drift.toFixed(3),
      usaRatio: (usa.drift / mx.drift).toFixed(2),
      spainRatio: (spain.drift / mx.drift).toFixed(2),
      mxVar: (mx.explained_var * 100).toFixed(1),
      usaVar: (usa.explained_var * 100).toFixed(1),
      spainVar: (spain.explained_var * 100).toFixed(1),
    };
  }, [crossCountry.data]);

  // Tab 4: COVID comparison from API
  const covid = useGet<CovidComparisonResponse>('/sensitivity/covid-comparison');

  // El diferencial 2%-8% se lee del barrido del sexo activo. Antes estaba escrito
  // en la prosa con el valor unisex y contradecia la tabla en los demas estados.
  const rateSpread = useMemo(() => {
    const results = wl.data?.results;
    if (!results) return null;
    const at = (i: number) => results.find((r) => Math.abs(r.interest_rate - i) < 1e-9)?.annual_premium;
    const p2 = at(0.02), p5 = at(0.05), p8 = at(0.08);
    if (p2 == null || p5 == null || p8 == null || p5 === 0) return null;
    return (((p2 - p8) / p5) * 100).toFixed(1);
  }, [wl.data]);

  // Igual con el COVID: drifts, freno y rango de primas salen de la respuesta.
  const covidFigures = useMemo(() => {
    const d = covid.data;
    if (!d || d.pre_covid.drift === 0) return null;
    const pcts = d.premium_impact.map((p) => p.pct_change);
    return {
      preDrift: d.pre_covid.drift.toFixed(3),
      fullDrift: d.full_period.drift.toFixed(3),
      slowdown: (((d.full_period.drift - d.pre_covid.drift) / Math.abs(d.pre_covid.drift)) * 100).toFixed(0),
      premiumMin: Math.min(...pcts).toFixed(1),
      premiumMax: Math.max(...pcts).toFixed(1),
    };
  }, [covid.data]);

  // Lazy-load: fetch cross-country and COVID data only when their tab is active
  const crossExecute = crossCountry.execute;
  const covidExecute = covid.execute;
  useEffect(() => {
    if (activeTab === 'comparison' && !crossCountry.data && !crossCountry.loading) {
      crossExecute();
    }
    if (activeTab === 'covid' && !covid.data && !covid.loading) {
      covidExecute();
    }
  }, [activeTab, crossExecute, covidExecute, crossCountry.data, crossCountry.loading, covid.data, covid.loading]);

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
    wl.execute({ product_type: 'whole_life', age, sum_assured: sumAssured, rates, sex });
    term.execute({ product_type: 'term', age, sum_assured: sumAssured, term: 20, rates, sex });
    endow.execute({ product_type: 'endowment', age, sum_assured: sumAssured, term: 20, rates, sex });

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
            sex,
          });
          return (res.data as SensitivityResponse).results.map((r) => r.annual_premium);
        })
      );
      setHeatmapData(results);
    } catch (err: unknown) {
      console.error('Heatmap fetch failed:', err);
    } finally {
      setHeatmapLoading(false);
    }
  };

  // El choque de mortalidad se lanza desde el boton y desde el reintento del
  // aviso de error, asi que la peticion vive en un solo lugar.
  const handleRunShock = () => {
    shockApi.execute({
      age: shockAge,
      sum_assured: sumAssured,
      product_type: shockProduct,
      factors: [-0.30, -0.20, -0.10, 0, 0.10, 0.20, 0.30],
      sex,
    });
  };

  const loading = wl.loading || term.loading || endow.loading || heatmapLoading;
  const interestError = wl.error ?? term.error ?? endow.error;

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
      {/* Page-level controls, labelled so the current state is never ambiguous */}
      <OptionGroup<SexKey>
        label={t('sensibilidad.controlSexLabel')}
        hint={t('sensibilidad.controlSexHint')}
        value={sex}
        onChange={setSex}
        options={[
          { value: 'unisex', label: t('forms.unisex') },
          { value: 'male', label: t('forms.male') },
          { value: 'female', label: t('forms.female') },
        ]}
      />

      <OptionGroup
        label={t('sensibilidad.controlViewLabel')}
        hint={t('sensibilidad.controlViewHint')}
        value={activeTab}
        onChange={setActiveTab}
        options={tabs.map((tab) => ({ value: tab.key, label: tab.label }))}
      />

      {/* Tab 1: Interest Rate */}
      {activeTab === 'interest_rate' && (
        <div data-demo-section="interest">
          <InsightCard variant="warning" title={t('sensibilidad.interestInsightTitle')}>
            <p>{t('sensibilidad.interestInsight')}</p>
          </InsightCard>
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
          {/* Las tres curvas se piden a la vez; si alguna falla no se dibuja
              nada y el panel queda vacio sin decir por que. */}
          {interestError && !loading && (
            <ErrorState message={interestError} onRetry={handleRunInterestRate} />
          )}

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
                {rateSpread && (
                  <p className={styles.narrative}>
                    {t('sensibilidad.interestSpreadNote', { spread: rateSpread })}
                  </p>
                )}
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
          <InsightCard variant="insight" title={t('sensibilidad.shockInsightTitle')}>
            <p>{t('sensibilidad.shockInsight')}</p>
          </InsightCard>
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
              onClick={handleRunShock}
              disabled={shockApi.loading}
              className={styles.runBtn}
            >
              {shockApi.loading ? t('sensibilidad.computing') : t('sensibilidad.runAnalysis')}
            </button>
          </div>

          {shockApi.loading && <LoadingState message={t('sensibilidad.loadingShock')} />}
          {shockApi.error && !shockApi.loading && (
            <ErrorState message={shockApi.error} onRetry={handleRunShock} />
          )}

          {shockApi.data && (
            <>
              <div className={styles.comparisonGrid}>
                <MetricBlock label={t('sensibilidad.' + productI18nKey[shockProduct])} value={`$${shockApi.data.base_premium.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} unit={`${t('tarificacion.ageLabel')} ${shockApi.data.age}`} />
                <MetricBlock label="+30% q_x" value={`+${shockApi.data.pct_changes[shockApi.data.pct_changes.length - 1]?.toFixed(1)}%`} unit={t('tables.premium')} />
                <MetricBlock label="-30% q_x" value={`${shockApi.data.pct_changes[0]?.toFixed(1)}%`} unit={t('tables.premium')} />
              </div>

              <LineChart
                traces={[{
                  x: shockApi.data.factors.map(f => `${(f * 100).toFixed(0)}%`),
                  y: shockApi.data.premiums,
                  name: `${t('sensibilidad.' + productI18nKey[shockProduct])} (${t('tarificacion.ageLabel')} ${shockAge})`,
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
          {/* El selector de sexo de la pagina no llega a esta vista: decirlo
              antes de los datos evita leerlos como respuesta a ese control. */}
          <p className={styles.footnote}>{t('sensibilidad.crossSexNote')}</p>
          {crossFigures && (
            <p className={styles.narrative}>
              {t('sensibilidad.crossIntro', crossFigures)}
            </p>
          )}

          {crossCountry.loading && <LoadingState message={t('sensibilidad.loadingCrossCountry')} />}
          {crossCountry.error && !crossCountry.loading && (
            <ErrorState message={crossCountry.error} onRetry={() => crossExecute()} />
          )}

          {crossCountry.data && (
            <>
              <div className={styles.comparisonGrid}>
                {crossCountry.data.countries.map(c => (
                  <MetricBlock key={c.country} label={`${t('tables.drift')} ${countryLabel(t, c.country)}`} value={c.drift.toFixed(3)} unit={t('inicio.yearUnit')} />
                ))}
              </div>

              <DataTable
                columns={crossColumns}
                data={crossCountry.data.countries.map(c => ({
                  country: countryLabel(t, c.country),
                  drift: c.drift,
                  explained_var: `${(c.explained_var * 100).toFixed(1)}%`,
                  q60: c.q60.toFixed(4),
                  premium_age40: `$${c.premium_age40.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                })) as unknown as Record<string, unknown>[]}
              />

              {/* k_t overlay */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.ktOverlay')}</h3>
                <LineChart
                  traces={crossCountry.data.kt_profiles.map((p, i) => ({
                    x: p.years,
                    y: p.kt,
                    name: countryLabel(t, p.country),
                    color: COUNTRY_COLORS[i % COUNTRY_COLORS.length],
                  }))}
                  xTitle={t('charts.year')}
                  yTitle="k_t"
                  height={350}
                />
                {crossFigures && (
                  <p className={styles.narrative}>{t('sensibilidad.ktCaption', crossFigures)}</p>
                )}
              </div>

              {/* a_x profiles */}
              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>{t('sensibilidad.axProfile')}</h3>
                <LineChart
                  traces={crossCountry.data.ax_profiles.map((p, i) => ({
                    x: p.ages,
                    y: p.values,
                    name: countryLabel(t, p.country),
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
                    name: countryLabel(t, p.country),
                    color: COUNTRY_COLORS[i % COUNTRY_COLORS.length],
                  }))}
                  xTitle={t('charts.age')}
                  yTitle="b_x"
                  height={300}
                />
                <p className={styles.narrative}>{t('sensibilidad.bxCaption')}</p>
              </div>

              {/* La lectura va despues de los datos que interpreta, y con las
                  mismas cifras que devolvio el motor. */}
              {crossFigures && (
                <InsightCard variant="info" title={t('sensibilidad.crossInsightTitle')}>
                  <p>{t('sensibilidad.crossInsight', crossFigures)}</p>
                </InsightCard>
              )}
            </>
          )}
        </div>
      )}

      {/* Tab 4: COVID Impact */}
      {activeTab === 'covid' && (
        <div data-demo-section="covid">
          {covidFigures && (
            <InsightCard variant="regulatory" title={t('sensibilidad.covidInsightTitle')}>
              <p>{t('sensibilidad.covidInsight', covidFigures)}</p>
            </InsightCard>
          )}
          <h3 className={styles.sectionTitle}>{t('sensibilidad.covidHeader')}</h3>
          {/* El endpoint compara ambos ajustes en unisex, igual que la vista de
              comparacion: decirlo evita leer las cifras como respuesta al selector. */}
          <p className={styles.footnote}>{t('sensibilidad.covidSexNote')}</p>
          {covidFigures && (
            <p className={styles.narrative}>
              {t('sensibilidad.covidIntro', covidFigures)}
            </p>
          )}

          {covid.loading && <LoadingState message={t('sensibilidad.loadingCovid')} />}
          {covid.error && !covid.loading && (
            <ErrorState message={covid.error} onRetry={() => covidExecute()} />
          )}

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
