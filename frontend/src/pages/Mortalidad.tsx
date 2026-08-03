import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import Section from '../components/layout/Section';
import SectionRail from '../components/layout/SectionRail';
import type { RailItem } from '../components/layout/SectionRail';
import OptionGroup from '../components/forms/OptionGroup';
import MetricBlock from '../components/data/MetricBlock';
import DataTable from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import LineChart from '../components/charts/LineChart';
import FanChart from '../components/charts/FanChart';
import FormulaBlock from '../components/data/FormulaBlock';
import InsightCard from '../components/data/InsightCard';
import MortalitySurface from '../components/charts/MortalitySurface';
import LoadingState from '../components/common/LoadingState';
import ErrorState from '../components/common/ErrorState';
import { useGet } from '../hooks/useApi';
import type {
  LeeCarterFitResponse,
  ProjectionResponse,
  ValidationResponse,
  GraduationResponse,
  MortalitySurfaceResponse,
  LCDiagnosticsResponse,
} from '../types';
import styles from './Mortalidad.module.css';

type SexKey = 'male' | 'female' | 'unisex';
type TableKey = 'cnsf' | 'cnsf_2013' | 'emssa_97';

function getValidationColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'age', label: t('tables.age'), align: 'right', numeric: true },
    { key: 'qx_ratio', label: t('tables.ratio'), align: 'right', numeric: true, format: (v) => Number(v).toFixed(4) },
    { key: 'qx_diff', label: t('tables.difference'), align: 'right', numeric: true, format: (v) => Number(v).toFixed(6) },
  ];
}

export default function Mortalidad() {
  const { t } = useTranslation();
  const [validationTab, setValidationTab] = useState<TableKey>('cnsf');
  const [sex, setSex] = useState<SexKey>('unisex');

  const validationColumns = useMemo(() => getValidationColumns(t), [t]);

  const railItems: RailItem[] = useMemo(() => [
    { id: 'sec-graduacion', step: '1', label: t('mortalidad.railGraduation') },
    { id: 'sec-superficie', step: '2', label: t('mortalidad.railSurface') },
    { id: 'sec-lee-carter', step: '3', label: t('mortalidad.railLeeCarter') },
    { id: 'sec-parametros', step: '4', label: t('mortalidad.railParams') },
    { id: 'sec-diagnosticos', step: '5', label: t('mortalidad.railDiagnostics') },
    { id: 'sec-proyeccion', step: '6', label: t('mortalidad.railProjection') },
    { id: 'sec-validacion', step: '7', label: t('mortalidad.railValidation') },
  ], [t]);

  const lc = useGet<LeeCarterFitResponse>('/mortality/lee-carter');
  const proj = useGet<ProjectionResponse>('/mortality/projection');
  const validation = useGet<ValidationResponse>('/mortality/validation');
  const graduation = useGet<GraduationResponse>('/mortality/graduation');
  const surface = useGet<MortalitySurfaceResponse>('/mortality/surface');
  const diagnostics = useGet<LCDiagnosticsResponse>('/mortality/diagnostics');
  const validationCnsf2013 = useGet<ValidationResponse>('/mortality/validation');
  const validationEmssa = useGet<ValidationResponse>('/mortality/validation');

  // useApi returns a stable `execute` (memoized on the endpoint), so we depend
  // on the destructured refs directly -- the effect re-runs only when `sex` changes.
  const { execute: runLc } = lc;
  const { execute: runProj } = proj;
  const { execute: runValidation } = validation;
  const { execute: runValidationCnsf2013 } = validationCnsf2013;
  const { execute: runGraduation } = graduation;
  const { execute: runSurface } = surface;
  const { execute: runDiagnostics } = diagnostics;
  const { execute: runValidationEmssa } = validationEmssa;

  useEffect(() => {
    runLc({ sex });
    runProj({ horizon: 30, projection_year: 2040, sex });
    runValidation({ projection_year: 2040, table_type: 'cnsf', sex });
    runValidationCnsf2013({ projection_year: 2040, table_type: 'cnsf_2013', sex });
    runGraduation({ sex });
    runSurface({ sex });
    runDiagnostics({ sex });
    runValidationEmssa({ projection_year: 2040, table_type: 'emssa_97', sex });
  }, [sex, runLc, runProj, runValidation, runValidationCnsf2013, runGraduation, runSurface, runDiagnostics, runValidationEmssa]);

  const activeValidation = validationTab === 'cnsf'
    ? validation
    : validationTab === 'cnsf_2013'
      ? validationCnsf2013
      : validationEmssa;

  // Cada tabla regulatoria se pide por separado, asi que una puede fallar sola
  // (p.ej. si la tabla CNSF 2013 no esta disponible en el entorno desplegado).
  // El reintento tiene que volver a pedir solo la pestaña activa.
  const retryActiveValidation = () => {
    const runActive = validationTab === 'cnsf'
      ? runValidation
      : validationTab === 'cnsf_2013'
        ? runValidationCnsf2013
        : runValidationEmssa;
    runActive({ projection_year: 2040, table_type: validationTab, sex });
  };

  return (
    <PageLayout
      title={t('mortalidad.title')}
      subtitle={t('mortalidad.subtitle')}
      rail={<SectionRail items={railItems} />}
    >
      {/* Page-level control: stated up front because it re-runs every section. */}
      <OptionGroup<SexKey>
        label={t('mortalidad.controlSexLabel')}
        hint={t('mortalidad.controlSexHint')}
        value={sex}
        onChange={setSex}
        options={[
          { value: 'unisex', label: t('forms.unisex') },
          { value: 'male', label: t('forms.male') },
          { value: 'female', label: t('forms.female') },
        ]}
      />

      {/* 1. Graduation: raw vs graduated */}
      {graduation.loading && <LoadingState message={t('mortalidad.loadingGraduation')} />}
      {/* Cada seccion se pinta con {x.data && ...}: si la peticion falla, la
          seccion simplemente desaparece y el lector no sabe si el modelo no
          tiene ese resultado o si el backend no respondio. El aviso con
          reintento es por seccion porque cada endpoint puede fallar solo. */}
      {graduation.error && !graduation.loading && (
        <ErrorState message={graduation.error} onRetry={() => runGraduation({ sex })} />
      )}

      {graduation.data && (
        <Section
          step="1"
          id="sec-graduacion"
          title={t('mortalidad.graduationTitle')}
          explainer={t('mortalidad.graduationExplainer')}
          demoSection="graduation"
        >
          <p className={styles.narrative}>{t('mortalidad.graduationDesc')}</p>
          <FormulaBlock
            src="/formulas/whittaker_henderson.png"
            alt="g_hat = (W + lambda D'D)^{-1} W m"
            label="Whittaker-Henderson"
            description="W = diagonal weight matrix (exposures), D = difference matrix (order 2), lambda = smoothing parameter"
          />
          <div className={styles.metricsRow}>
            <MetricBlock
              label="Lambda"
              value={graduation.data.lambda_param.toLocaleString()}
            />
            <MetricBlock
              label={t('mortalidad.roughnessReduction')}
              value={`${(graduation.data.roughness_reduction * 100).toFixed(1)}%`}
            />
            <MetricBlock
              label={t('mortalidad.roughnessRaw')}
              value={graduation.data.roughness_raw.toFixed(6)}
            />
            <MetricBlock
              label={t('mortalidad.roughnessGrad')}
              value={graduation.data.roughness_graduated.toFixed(6)}
            />
          </div>
          <LineChart
            traces={[
              {
                x: graduation.data.ages,
                y: graduation.data.raw_mx.map(v => Math.log(v)),
                name: t('mortalidad.rawMx'),
                color: '#9E9E9E',
              },
              {
                x: graduation.data.ages,
                y: graduation.data.graduated_mx.map(v => Math.log(v)),
                name: t('mortalidad.graduatedMx'),
                color: '#C41E3A',
              },
            ]}
            xTitle={t('charts.age')}
            yTitle={t('charts.lnMx')}
            height={400}
          />
          <InsightCard variant="insight" title={t('mortalidad.graduationInsightTitle')}>
            <p>{t('mortalidad.graduationInsight')}</p>
          </InsightCard>
        </Section>
      )}

      {/* 2. Mortality Surface (3D) */}
      {surface.loading && <LoadingState message={t('mortalidad.loadingSurface')} />}
      {surface.error && !surface.loading && (
        <ErrorState message={surface.error} onRetry={() => runSurface({ sex })} />
      )}

      {surface.data && (
        <Section
          step="2"
          id="sec-superficie"
          title={t('mortalidad.surfaceTitle')}
          explainer={t('mortalidad.surfaceExplainer')}
          demoSection="surface"
        >
          <p className={styles.narrative}>{t('mortalidad.surfaceDesc')}</p>
          <MortalitySurface
            ages={surface.data.ages}
            years={surface.data.years}
            values={surface.data.log_mx}
            title="log(m_{x,t})"
            height={500}
          />
          <InsightCard variant="info" title={t('mortalidad.surfaceInsightTitle')}>
            <p>{t('mortalidad.surfaceInsight')}</p>
          </InsightCard>
        </Section>
      )}

      {/* 3. Lee-Carter formula + fit */}
      {lc.loading && <LoadingState message={t('mortalidad.fitting')} />}
      {lc.error && !lc.loading && (
        <ErrorState message={lc.error} onRetry={() => runLc({ sex })} />
      )}

      {lc.data && (
        <>
          <Section
            step="3"
            id="sec-lee-carter"
            title={t('mortalidad.lcTitle')}
            explainer={t('mortalidad.lcExplainer')}
            demoSection="lee-carter"
          >
            <FormulaBlock
              src="/formulas/lee_carter.png"
              alt="ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}"
              label={t('mortalidad.lcModel')}
              description="a_x = average log-mortality by age, b_x = age sensitivity to change, k_t = temporal index"
            />
            <div className={styles.metricsRow}>
              <MetricBlock
                label={t('mortalidad.explainedVar')}
                value={`${(lc.data.explained_variance * 100).toFixed(1)}%`}
              />
              <MetricBlock
                label={t('mortalidad.drift')}
                value={lc.data.drift.toFixed(3)}
              />
              <MetricBlock
                label={t('mortalidad.sigma')}
                value={lc.data.sigma.toFixed(3)}
              />
              <MetricBlock
                label={t('mortalidad.ageRange')}
                value={`${lc.data.ages[0]} - ${lc.data.ages[lc.data.ages.length - 1]}`}
              />
            </div>
          </Section>

          <Section
            step="4"
            id="sec-parametros"
            title={t('mortalidad.paramsTitle')}
            explainer={t('mortalidad.paramsExplainer')}
          >
            <div className={styles.chartGrid}>
              <div>
                <h3 className={styles.chartTitle}>{t('mortalidad.axTitle')}</h3>
                <LineChart
                  traces={[{
                    x: lc.data.ages,
                    y: lc.data.ax,
                    name: 'a_x',
                    color: '#000',
                  }]}
                  xTitle={t('charts.age')}
                  yTitle="a_x"
                  height={300}
                />
              </div>
              <div>
                <h3 className={styles.chartTitle}>{t('mortalidad.bxTitle')}</h3>
                <LineChart
                  traces={[{
                    x: lc.data.ages,
                    y: lc.data.bx,
                    name: 'b_x',
                    color: '#C41E3A',
                  }]}
                  xTitle={t('charts.age')}
                  yTitle="b_x"
                  height={300}
                />
              </div>
              <div>
                <h3 className={styles.chartTitle}>{t('mortalidad.ktTitle')}</h3>
                <LineChart
                  traces={[{
                    x: lc.data.years,
                    y: lc.data.kt,
                    name: 'k_t',
                    color: '#424242',
                  }]}
                  xTitle={t('charts.year')}
                  yTitle="k_t"
                  height={300}
                />
              </div>
            </div>
          </Section>
        </>
      )}

      {/* 5. SVD Diagnostics */}
      {diagnostics.loading && <LoadingState message={t('mortalidad.loadingDiagnostics')} />}
      {diagnostics.error && !diagnostics.loading && (
        <ErrorState message={diagnostics.error} onRetry={() => runDiagnostics({ sex })} />
      )}

      {diagnostics.data && (
        <Section
          step="5"
          id="sec-diagnosticos"
          title={t('mortalidad.svdTitle')}
          explainer={t('mortalidad.svdExplainer')}
        >
          <p className={styles.narrative}>{t('mortalidad.svdDesc')}</p>
          <div className={styles.metricsRow}>
            <MetricBlock label={t('mortalidad.rmse')} value={diagnostics.data.rmse.toFixed(6)} />
            <MetricBlock label={t('mortalidad.maxAbsError')} value={diagnostics.data.max_abs_error.toFixed(6)} />
            <MetricBlock label={t('mortalidad.meanAbsError')} value={diagnostics.data.mean_abs_error.toFixed(6)} />
            <MetricBlock label={t('mortalidad.explainedVar')} value={`${(diagnostics.data.explained_variance * 100).toFixed(1)}%`} />
          </div>
          <InsightCard variant="insight" title={t('mortalidad.svdInsightTitle')}>
            <p>{t('mortalidad.svdInsight')}</p>
          </InsightCard>
        </Section>
      )}

      {/* 6. Projection */}
      {proj.loading && <LoadingState message={t('mortalidad.projecting')} />}
      {proj.error && !proj.loading && (
        <ErrorState
          message={proj.error}
          onRetry={() => runProj({ horizon: 30, projection_year: 2040, sex })}
        />
      )}

      {proj.data && (
        <Section
          step="6"
          id="sec-proyeccion"
          title={t('mortalidad.projTitle')}
          explainer={t('mortalidad.projExplainer')}
          demoSection="projection"
        >
          <div className={styles.metricsRow}>
            <MetricBlock label={t('mortalidad.drift')} value={proj.data.drift.toFixed(3)} />
          </div>
          <FanChart
            x={proj.data.projected_years}
            central={proj.data.kt_central}
            lower={proj.data.kt_central.map((v, i) =>
              v - 1.96 * proj.data!.sigma * Math.sqrt(i + 1)
            )}
            upper={proj.data.kt_central.map((v, i) =>
              v + 1.96 * proj.data!.sigma * Math.sqrt(i + 1)
            )}
            xTitle={t('charts.year')}
            yTitle="k_t"
            height={400}
          />
        </Section>
      )}

      {/* 7. Validation with CNSF/EMSSA tabs */}
      {(validation.loading || validationCnsf2013.loading || validationEmssa.loading) && (
        <LoadingState message={t('mortalidad.loadingValidation')} />
      )}

      {/* La seccion tambien se muestra en error: si se ocultara, las tres tablas
          caidas dejarian desaparecer el paso 7 completo del recorrido. */}
      {(validation.data || validationCnsf2013.data || validationEmssa.data
        || activeValidation.error) && (
        <Section
          step="7"
          id="sec-validacion"
          title={t('mortalidad.validationTitle')}
          explainer={t('mortalidad.validationExplainer')}
          demoSection="validation"
        >
          <ul className={styles.narrative}>
            <li>{t('mortalidad.validationDescRatio')}</li>
            <li>{t('mortalidad.validationDescDiff')}</li>
            <li>{t('mortalidad.validationDescOptimistic')}</li>
            <li>{t('mortalidad.validationDescConservative')}</li>
          </ul>

          <OptionGroup<TableKey>
            label={t('mortalidad.controlTableLabel')}
            hint={t('mortalidad.controlTableHint')}
            value={validationTab}
            onChange={setValidationTab}
            options={[
              { value: 'cnsf', label: t('mortalidad.validationCnsf') },
              { value: 'cnsf_2013', label: t('mortalidad.validationCnsf2013') },
              { value: 'emssa_97', label: t('mortalidad.validationEmssa') },
            ]}
          />

          {activeValidation.error && !activeValidation.loading && (
            <ErrorState message={activeValidation.error} onRetry={retryActiveValidation} />
          )}

          {activeValidation.data && (
            <>
              <div className={styles.metricsRow}>
                <MetricBlock label="RMSE" value={activeValidation.data.rmse.toFixed(6)} />
                <MetricBlock label={t('tables.meanRatio')} value={activeValidation.data.mean_ratio.toFixed(3)} />
                <MetricBlock label={t('tables.ages')} value={activeValidation.data.n_ages} />
              </div>
              <DataTable
                columns={validationColumns}
                data={activeValidation.data.ages.map((age, i) => ({
                  age,
                  qx_ratio: activeValidation.data!.qx_ratios[i],
                  qx_diff: activeValidation.data!.qx_differences[i],
                }))}
              />
            </>
          )}
        </Section>
      )}
    </PageLayout>
  );
}
