import { useEffect } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import FormulaBlock from '../components/data/FormulaBlock';
import InsightCard from '../components/data/InsightCard';
import MetricBlock from '../components/data/MetricBlock';
import DeepDiveLink from '../components/data/DeepDiveLink';
import ErrorState from '../components/common/ErrorState';
import { useGet, usePost } from '../hooks/useApi';
import PageLayout from '../components/layout/PageLayout';
import type {
  CrossCountryResponse,
  CrossCountryEntry,
  SCRResponse,
  CovidComparisonResponse,
  SensitivityResponse,
  MortalityShockRequest,
  MortalityShockResponse,
} from '../types';
import { compactMoney, countryKey, wholeMoney } from '../utils/format';
import styles from './Metodologia.module.css';

// --- Live-value formatting helpers (M3: no hardcoded actuarial numbers) ---
const DASH = '—';
const pct = (frac?: number, digits = 1) =>
  frac == null ? DASH : `${(frac * 100).toFixed(digits)}%`;
const pctRaw = (value?: number, digits = 1) =>
  value == null ? DASH : `${value.toFixed(digits)}%`;
const pctSigned = (value?: number, digits = 1) =>
  value == null ? DASH : `${value > 0 ? '+' : ''}${value.toFixed(digits)}%`;
const signed = (v?: number, digits = 3) => (v == null ? DASH : v.toFixed(digits));
// Prima a peso entero: la seccion 05 muestra importes de cuatro y cinco cifras.
const money = (v?: number) => (v == null ? DASH : wholeMoney(v));
// Escala compacta con umbral, la misma que usa /scr: un RCS de 809,207 se lee
// "$809.2K" en las dos paginas y no queda descuadrado junto a "$5.30M".
const scaled = (v?: number) => (v == null ? DASH : compactMoney(v));

interface SectionProps {
  number: string;
  title: string;
  children: React.ReactNode;
}

function Section({ number, title, children }: SectionProps) {
  return (
    <section className={styles.section}>
      <div className={styles.sectionNumber}>{number}</div>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children}
    </section>
  );
}

export default function Metodologia() {
  const { t } = useTranslation();

  // Live model values -- replace previously hardcoded actuarial numbers (M3).
  const cross = useGet<CrossCountryResponse>('/sensitivity/cross-country');
  const scr = usePost<object, SCRResponse>('/scr/defaults');
  const covid = useGet<CovidComparisonResponse>('/sensitivity/covid-comparison');
  // Seccion 05: las primas y el choque de mortalidad se calculan aqui mismo en vez
  // de citarse. Base fija y declarada en el texto: vida entera, edad 40, SA 1,000,000,
  // tabla unisex. Tarificacion parte del ajuste masculino, de ahi que su prima difiera.
  const rateSweep = usePost<object, SensitivityResponse>('/pricing/sensitivity');
  const mortShock = usePost<MortalityShockRequest, MortalityShockResponse>(
    '/sensitivity/mortality-shock',
  );

  const { execute: runCross } = cross;
  const { execute: runScr } = scr;
  const { execute: runCovid } = covid;
  const { execute: runRateSweep } = rateSweep;
  const { execute: runMortShock } = mortShock;

  useEffect(() => {
    runCross();
    runScr({});
    runCovid();
    runRateSweep({
      product_type: 'whole_life',
      age: 40,
      sum_assured: 1_000_000,
      rates: [0.02, 0.05, 0.08],
      sex: 'unisex',
    });
    runMortShock({
      age: 40,
      sum_assured: 1_000_000,
      product_type: 'whole_life',
      factors: [0, 0.3],
      sex: 'unisex',
    });
  }, [runCross, runScr, runCovid, runRateSweep, runMortShock]);

  // --- Derived values fed into prose and metric blocks ---
  // Se empareja por clave normalizada: el nombre llega acentuado desde la API y
  // una comparacion literal se rompe con cualquier cambio de ortografia.
  const country = (key: 'mexico' | 'usa' | 'spain'): CrossCountryEntry | undefined =>
    cross.data?.countries.find((c) => countryKey(c.country) === key);
  const mx = country('mexico');
  const spain = country('spain');
  const usa = country('usa');

  const scrData = scr.data;
  const totalScr = scrData?.total_aggregation.scr_aggregated;
  const techProv = scrData?.technical_provisions;
  const divPct = scrData?.total_aggregation.diversification_pct;
  const irDominancePct = scrData
    ? (scrData.interest_rate.scr / scrData.total_aggregation.scr_aggregated) * 100
    : undefined;

  const covidDrift = covid.data?.full_period.drift;
  const premiumPcts = covid.data?.premium_impact.map((p) => p.pct_change);
  const premiumMin = premiumPcts?.length ? Math.min(...premiumPcts) : undefined;
  const premiumMax = premiumPcts?.length ? Math.max(...premiumPcts) : undefined;

  const rateAt = (i: number) =>
    rateSweep.data?.results.find((r) => Math.abs(r.interest_rate - i) < 1e-9)?.annual_premium;
  const premium2 = rateAt(0.02);
  const premium5 = rateAt(0.05);
  const premium8 = rateAt(0.08);
  // (P al 2% - P al 8%) / P al 5%: el denominador es la prima base, no un extremo.
  const rateSpreadPct =
    premium2 != null && premium5 != null && premium8 != null
      ? ((premium2 - premium8) / premium5) * 100
      : undefined;
  const shockIdx = mortShock.data?.factors.findIndex((f) => Math.abs(f - 0.3) < 1e-9);
  const shock30Pct =
    shockIdx != null && shockIdx >= 0 ? mortShock.data?.pct_changes[shockIdx] : undefined;

  const belTotal = scrData?.bel_base;
  const belShare = (part?: number) =>
    part == null || !belTotal ? undefined : (part / belTotal) * 100;

  // Toda la pagina se degrada a guiones (DASH) si la API falla, lo cual es
  // silencioso: el lector no distingue "no hay dato" de "el backend no
  // respondio". Un solo aviso con reintento cubre las tres peticiones.
  const loadError =
    cross.error ?? scr.error ?? covid.error ?? rateSweep.error ?? mortShock.error;
  const anyLoading =
    cross.loading || scr.loading || covid.loading || rateSweep.loading || mortShock.loading;
  const retryAll = () => {
    runCross();
    runScr({});
    runCovid();
    runRateSweep({
      product_type: 'whole_life',
      age: 40,
      sum_assured: 1_000_000,
      rates: [0.02, 0.05, 0.08],
      sex: 'unisex',
    });
    runMortShock({
      age: 40,
      sum_assured: 1_000_000,
      product_type: 'whole_life',
      factors: [0, 0.3],
      sex: 'unisex',
    });
  };

  // <Trans> comparte el mismo marcado tipografico en las siete narrativas.
  const proseTags = {
    em: <em />,
    hl: <span className={styles.highlight} />,
  };

  return (
    <PageLayout title={t('metodologia.title')} subtitle={t('metodologia.subtitle')}>
      <div data-demo-section="top" />
      <InsightCard variant="insight" title={t('metodologia.portfolioFramingTitle')}>
        <p>{t('metodologia.portfolioFraming')}</p>
      </InsightCard>

      {loadError && !anyLoading && (
        <ErrorState message={loadError} onRetry={retryAll} />
      )}

      {/* SECTION 1: DATOS */}
      <Section number="01" title={t('metodologia.sections.datos')}>
        <p className={styles.narrative}>
          <Trans i18nKey="metodologia.narrative.datos" components={proseTags} />
        </p>
        <FormulaBlock
          src="/formulas/central_death_rate.png"
          alt="m_{x,t} = D_{x,t} / E_{x,t}"
          label={t('metodologia.formulaLabels.centralDeathRate')}
          description={t('metodologia.formulaDescriptions.centralDeathRate')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.dataYears')} value="30" unit={t('metodologia.metrics.yearsUnit')} />
          <MetricBlock label={t('metodologia.metrics.ageRange')} value="0 - 100" />
          <MetricBlock label={t('metodologia.metrics.dataSource')} value="INEGI / CONAPO" />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.seeMortality')} to="/mortalidad" />
        </div>
      </Section>

      {/* SECTION 2: GRADUACION */}
      <Section number="02" title={t('metodologia.sections.graduacion')}>
        <p className={styles.narrative}>
          <Trans i18nKey="metodologia.narrative.graduacion" components={proseTags} />
        </p>
        <FormulaBlock
          src="/formulas/whittaker_henderson.png"
          alt="g_hat = (W + lambda D'D)^{-1} W m"
          label={t('metodologia.formulaLabels.graduation')}
          description={t('metodologia.formulaDescriptions.graduation')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label="Lambda" value="100,000" />
          <MetricBlock label={t('metodologia.metrics.differenceOrder')} value="2" />
          <MetricBlock label={t('metodologia.metrics.weights')} value={t('metodologia.metrics.exposures')} />
        </div>
      </Section>

      {/* SECTION 3: LEE-CARTER */}
      <Section number="03" title={t('metodologia.sections.leeCarter')}>
        <p className={styles.narrative}>
          <Trans
            i18nKey="metodologia.narrative.leeCarter"
            components={proseTags}
            values={{
              mxVar: pct(mx?.explained_var),
              spainVar: pct(spain?.explained_var),
              usaVar: pct(usa?.explained_var),
            }}
          />
        </p>
        <FormulaBlock
          src="/formulas/lee_carter.png"
          alt="ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}"
          label={t('metodologia.formulaLabels.leeCarter')}
          description={t('metodologia.formulaDescriptions.leeCarter')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.explainedVar')} value={pct(mx?.explained_var)} />
          <MetricBlock label={t('metodologia.metrics.method')} value="SVD" />
          <MetricBlock label={t('metodologia.metrics.constraints')} value={t('metodologia.metrics.identifiability')} />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.seeParameters')} to="/mortalidad" />
        </div>
      </Section>

      {/* SECTION 4: PROYECCION */}
      <Section number="04" title={t('metodologia.sections.proyeccion')}>
        <p className={styles.narrative}>
          <Trans
            i18nKey="metodologia.narrative.proyeccion"
            components={proseTags}
            values={{
              mxDrift: signed(mx?.drift),
              spainDrift: signed(spain?.drift),
              usaDrift: signed(usa?.drift),
              covidDrift: signed(covidDrift),
              premiumMin: pctRaw(premiumMin),
              premiumMax: pctRaw(premiumMax),
            }}
          />
        </p>
        <FormulaBlock
          src="/formulas/rwd.png"
          alt="k_{t+1} = k_t + d + sigma * Z_t, Z_t ~ N(0,1)"
          label={t('metodologia.formulaLabels.rwd')}
          description={t('metodologia.formulaDescriptions.rwd')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.driftMexico')} value={signed(mx?.drift)} unit={t('metodologia.metrics.perYear')} />
          <MetricBlock label={t('metodologia.metrics.driftSpain')} value={signed(spain?.drift)} unit={t('metodologia.metrics.perYear')} />
          <MetricBlock label={t('metodologia.metrics.driftUSA')} value={signed(usa?.drift)} unit={t('metodologia.metrics.perYear')} />
        </div>
      </Section>

      {/* SECTION 5: TARIFICACION */}
      <Section number="05" title={t('metodologia.sections.tarificacion')}>
        <p className={styles.narrative}>
          <Trans
            i18nKey="metodologia.narrative.tarificacion"
            components={proseTags}
            values={{
              premium2: money(premium2),
              premium5: money(premium5),
              premium8: money(premium8),
              rateSpread: pctRaw(rateSpreadPct),
              mortShock: pctSigned(shock30Pct, 2),
            }}
          />
        </p>
        <FormulaBlock
          src="/formulas/whole_life_premium.png"
          alt="P = SA * M_x / N_x"
          label={t('metodologia.formulaLabels.wholeLifePremium')}
          description={t('metodologia.formulaDescriptions.wholeLifePremium')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.premiumAge40')} value={money(premium5)} />
          <MetricBlock label={t('metodologia.metrics.rateSpread')} value={pctRaw(rateSpreadPct)} />
          <MetricBlock label={t('metodologia.metrics.mortalityImpact')} value={pctSigned(shock30Pct, 2)} />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.calculatePremiums')} to="/tarificacion" />
        </div>
      </Section>

      {/* SECTION 6: RESERVAS */}
      <Section number="06" title={t('metodologia.sections.reservas')}>
        <p className={styles.narrative}>
          <Trans i18nKey="metodologia.narrative.reservas" components={proseTags} />
        </p>
        <FormulaBlock
          src="/formulas/prospective_reserve.png"
          alt="tV = SA * A_{x+t} - P * a-double-dot_{x+t}"
          label={t('metodologia.formulaLabels.prospectiveReserve')}
          description={t('metodologia.formulaDescriptions.prospectiveReserve')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.belTotal')} value={scaled(belTotal)} />
          <MetricBlock
            label={t('metodologia.metrics.belAnnuity')}
            value={scaled(scrData?.bel_annuity)}
            unit={`(${pctRaw(belShare(scrData?.bel_annuity), 0)})`}
          />
          <MetricBlock
            label={t('metodologia.metrics.belDeath')}
            value={scaled(scrData?.bel_death)}
            unit={`(${pctRaw(belShare(scrData?.bel_death), 0)})`}
          />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.seePricing')} to="/tarificacion" />
        </div>
      </Section>

      {/* SECTION 7: RCS */}
      <Section number="07" title={t('metodologia.sections.rcs')}>
        <p className={styles.narrative}>
          <Trans
            i18nKey="metodologia.narrative.rcs"
            components={proseTags}
            values={{
              divPct: pctRaw(divPct),
              totalScr: scaled(totalScr),
              techProv: scaled(techProv),
              irPct: pctRaw(irDominancePct),
            }}
          />
        </p>
        <FormulaBlock
          src="/formulas/rcs_aggregation.png"
          alt="RCS = sqrt(S^T * C * S)"
          label={t('metodologia.formulaLabels.scrAggregation')}
          description={t('metodologia.formulaDescriptions.scrAggregation')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.totalSCR')} value={scaled(totalScr)} />
          <MetricBlock label={t('metodologia.metrics.techProvisions')} value={scaled(techProv)} />
          <MetricBlock label={t('metodologia.metrics.diversification')} value={pctRaw(divPct)} />
          <MetricBlock
            label={t('metodologia.metrics.dominantRisk')}
            value={t('metodologia.metrics.interestRateRisk')}
            unit={`(${pctRaw(irDominancePct)})`}
          />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.seeSCR')} to="/scr" />
        </div>
      </Section>
      {/* SECTION 8: RECURSOS */}
      <Section number="08" title={t('metodologia.sections.recursos')}>
        <p className={styles.narrative}>
          {t('metodologia.recursosDesc')}
        </p>
        <div className={styles.resourcesGrid}>
          {[
            { titleKey: 'metodologia.resources.leeCarter.title', descKey: 'metodologia.resources.leeCarter.desc', pdfPath: '/docs/lee_carter_reestimation.pdf', pages: '~16 pp.' },
            { titleKey: 'metodologia.resources.graduation.title', descKey: 'metodologia.resources.graduation.desc', pdfPath: '/docs/graduation_reestimation_intuition.pdf', pages: '~10 pp.' },
            { titleKey: 'metodologia.resources.quadratic.title', descKey: 'metodologia.resources.quadratic.desc', pdfPath: '/docs/quadratic_minimization_matrix.pdf', pages: '~9 pp.' },
            { titleKey: 'metodologia.resources.svd.title', descKey: 'metodologia.resources.svd.desc', pdfPath: '/docs/svd_bilinear_identifiability_lee_carter.pdf', pages: '~10 pp.' },
            { titleKey: 'metodologia.resources.whittaker.title', descKey: 'metodologia.resources.whittaker.desc', pdfPath: '/docs/whittaker_henderson_graduation.pdf', pages: '~11 pp.' },
            { titleKey: 'metodologia.resources.euGender.title', descKey: 'metodologia.resources.euGender.desc', pdfPath: '/docs/eu_gender_directive_unisex_pricing.pdf', pages: '~29 pp.' },
          ].map((res) => (
            <a key={res.pdfPath} href={res.pdfPath} target="_blank" rel="noopener noreferrer" className={styles.resourceCard} style={{ textDecoration: 'none', color: 'inherit' }}>
              <div className={styles.resourceTitle}>{t(res.titleKey)}</div>
              <div className={styles.resourceDesc}>{t(res.descKey)}</div>
              <div className={styles.resourceMeta}>
                <span className={styles.resourcePages}>{res.pages}</span>
                <span className={styles.resourcePath}>PDF</span>
              </div>
            </a>
          ))}
        </div>
      </Section>
    </PageLayout>
  );
}
