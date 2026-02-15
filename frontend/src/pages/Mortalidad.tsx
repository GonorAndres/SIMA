import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import MetricBlock from '../components/data/MetricBlock';
import DataTable from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import LineChart from '../components/charts/LineChart';
import FanChart from '../components/charts/FanChart';
import FormulaBlock from '../components/data/FormulaBlock';
import MortalitySurface from '../components/charts/MortalitySurface';
import LoadingState from '../components/common/LoadingState';
import { useGet } from '../hooks/useApi';
import type {
  LeeCaterFitResponse,
  ProjectionResponse,
  ValidationResponse,
  GraduationResponse,
  MortalitySurfaceResponse,
  LCDiagnosticsResponse,
} from '../types';
import styles from './Mortalidad.module.css';

function getValidationColumns(t: (key: string) => string): Column[] {
  return [
    { key: 'age', label: t('tables.age'), align: 'right', numeric: true },
    { key: 'qx_ratio', label: t('tables.ratio'), align: 'right', numeric: true, format: (v) => Number(v).toFixed(4) },
    { key: 'qx_diff', label: t('tables.difference'), align: 'right', numeric: true, format: (v) => Number(v).toFixed(6) },
  ];
}

export default function Mortalidad() {
  const { t } = useTranslation();
  const [validationTab, setValidationTab] = useState<'cnsf' | 'emssa'>('cnsf');

  const validationColumns = useMemo(() => getValidationColumns(t), [t]);

  const lc = useGet<LeeCaterFitResponse>('/mortality/lee-carter');
  const proj = useGet<ProjectionResponse>('/mortality/projection');
  const validation = useGet<ValidationResponse>('/mortality/validation');
  const graduation = useGet<GraduationResponse>('/mortality/graduation');
  const surface = useGet<MortalitySurfaceResponse>('/mortality/surface');
  const diagnostics = useGet<LCDiagnosticsResponse>('/mortality/diagnostics');
  const validationEmssa = useGet<ValidationResponse>('/mortality/validation');

  useEffect(() => {
    lc.execute();
    proj.execute({ horizon: 30, projection_year: 2040 });
    validation.execute({ projection_year: 2040, table_type: 'cnsf' });
    graduation.execute();
    surface.execute();
    diagnostics.execute();
    validationEmssa.execute({ projection_year: 2040, table_type: 'emssa' });
  }, []);

  const activeValidation = validationTab === 'cnsf' ? validation : validationEmssa;

  return (
    <PageLayout
      title={t('mortalidad.title')}
      subtitle={t('mortalidad.subtitle')}
    >
      {/* 1. Graduation: raw vs graduated */}
      {graduation.loading && <LoadingState message={t('mortalidad.loadingGraduation')} />}

      {graduation.data && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>{t('mortalidad.graduationTitle')}</h3>
          <p className={styles.narrative}>
            {t('mortalidad.graduationDesc')}
          </p>
          <FormulaBlock
            latex="\\hat{g} = \\left(W + \\lambda D'D\\right)^{-1} W \\, m"
            label="Whittaker-Henderson"
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
        </div>
      )}

      {/* 2. Mortality Surface (3D) */}
      {surface.loading && <LoadingState message={t('mortalidad.loadingSurface')} />}

      {surface.data && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>{t('mortalidad.surfaceTitle')}</h3>
          <p className={styles.narrative}>
            {t('mortalidad.surfaceDesc')}
          </p>
          <MortalitySurface
            ages={surface.data.ages}
            years={surface.data.years}
            values={surface.data.log_mx}
            title="log(m_{x,t})"
            height={500}
          />
        </div>
      )}

      {/* 3. Lee-Carter formula + fit */}
      <FormulaBlock
        latex="\\ln(m_{x,t}) = a_x + b_x \\cdot k_t + \\varepsilon_{x,t}"
        label={t('mortalidad.lcModel')}
      />

      {lc.loading && <LoadingState message={t('mortalidad.fitting')} />}
      {lc.error && <p className={styles.errorText}>Error: {lc.error}</p>}

      {lc.data && (
        <>
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

          {/* Three charts side by side */}
          <div className={styles.section}>
            <div className={styles.chartGrid}>
              <div>
                <h3 className={styles.sectionTitle}>{t('mortalidad.axTitle')}</h3>
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
                <h3 className={styles.sectionTitle}>{t('mortalidad.bxTitle')}</h3>
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
                <h3 className={styles.sectionTitle}>{t('mortalidad.ktTitle')}</h3>
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
          </div>
        </>
      )}

      {/* 5. SVD Diagnostics */}
      {diagnostics.loading && <LoadingState message={t('mortalidad.loadingDiagnostics')} />}

      {diagnostics.data && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>{t('mortalidad.svdTitle')}</h3>
          <p className={styles.narrative}>
            {t('mortalidad.svdDesc')}
          </p>
          <div className={styles.metricsRow}>
            <MetricBlock label={t('mortalidad.rmse')} value={diagnostics.data.rmse.toFixed(6)} />
            <MetricBlock label={t('mortalidad.maxAbsError')} value={diagnostics.data.max_abs_error.toFixed(6)} />
            <MetricBlock label={t('mortalidad.meanAbsError')} value={diagnostics.data.mean_abs_error.toFixed(6)} />
            <MetricBlock label={t('mortalidad.explainedVar')} value={`${(diagnostics.data.explained_variance * 100).toFixed(1)}%`} />
          </div>
        </div>
      )}

      {/* 6. Projection */}
      {proj.loading && <LoadingState message={t('mortalidad.projecting')} />}

      {proj.data && (
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>{t('mortalidad.projTitle')}</h3>
          <MetricBlock label={t('mortalidad.drift')} value={proj.data.drift.toFixed(3)} />
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
        </div>
      )}

      {/* 7. Validation with CNSF/EMSSA tabs */}
      {(validation.loading || validationEmssa.loading) && (
        <LoadingState message={t('mortalidad.loadingValidation')} />
      )}

      {(validation.data || validationEmssa.data) && (
        <div className={styles.validationSection}>
          <h3 className={styles.sectionTitle}>{t('mortalidad.validationTitle')}</h3>

          <div className={styles.validationTabs}>
            <button
              className={`${styles.validationTab} ${validationTab === 'cnsf' ? styles.validationTabActive : ''}`}
              onClick={() => setValidationTab('cnsf')}
            >
              {t('mortalidad.validationCnsf')}
            </button>
            <button
              className={`${styles.validationTab} ${validationTab === 'emssa' ? styles.validationTabActive : ''}`}
              onClick={() => setValidationTab('emssa')}
            >
              {t('mortalidad.validationEmssa')}
            </button>
          </div>

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
        </div>
      )}
    </PageLayout>
  );
}
