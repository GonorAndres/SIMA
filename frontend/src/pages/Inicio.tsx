import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import MetricBlock from '../components/data/MetricBlock';
import DeepDiveLink from '../components/data/DeepDiveLink';
import LineChart from '../components/charts/LineChart';
import LoadingState from '../components/common/LoadingState';
import { useGet, usePost } from '../hooks/useApi';
import type { LeeCarterFitResponse, SCRResponse } from '../types';
import styles from './Inicio.module.css';

export default function Inicio() {
  const { t } = useTranslation();
  const lc = useGet<LeeCarterFitResponse>('/mortality/lee-carter');
  const scr = usePost<object, SCRResponse>('/scr/compute');

  useEffect(() => {
    lc.execute();
    scr.execute({ available_capital: 1_000_000 });
  }, []);

  return (
    <PageLayout>
      {/* Hero: 5:1 split -- context left, stats right */}
      <div className={styles.hero}>
        <div className={styles.heroLeft}>
          <h1 className={styles.projectTitle}>{t('inicio.title')}</h1>
          <p className={styles.projectDesc}>{t('inicio.desc')}</p>

          <div className={styles.context}>
            <h2 className={styles.contextTitle}>{t('inicio.contextTitle')}</h2>
            <p className={styles.contextParagraph}>{t('inicio.contextP1')}</p>
            <p className={styles.contextParagraph}>{t('inicio.contextP2')}</p>
            <p className={styles.contextParagraph}>{t('inicio.contextP3')}</p>
            <p className={styles.contextParagraph}>
              {t('inicio.contextP4')}
              {' '}
              <a
                href="https://github.com/GonorAndres/SIMA"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.githubLink}
              >
                <svg className={styles.githubIcon} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GonorAndres/SIMA
              </a>
            </p>
          </div>
        </div>

        <div className={styles.heroRight}>
          <div className={styles.statsLabel}>{t('inicio.statsTitle')}</div>

          {lc.loading && <LoadingState message={t('inicio.loadingMortality')} />}
          {scr.loading && <LoadingState message={t('inicio.loadingSCR')} />}

          {lc.data && (
            <>
              <MetricBlock
                label={t('inicio.explainedVar')}
                value={`${(lc.data.explained_variance * 100).toFixed(1)}%`}
              />
              <MetricBlock
                label={t('inicio.drift')}
                value={lc.data.drift.toFixed(3)}
              />
              <MetricBlock
                label={t('inicio.dataYears')}
                value={lc.data.years.length}
              />
            </>
          )}

          {scr.data && (
            <>
              <MetricBlock
                label={t('inicio.scrTotal')}
                value={`$${(scr.data.total_aggregation.scr_aggregated / 1000).toFixed(1)}K`}
              />
              {scr.data.solvency && (
                <MetricBlock
                  label={t('inicio.solvencyRatio')}
                  value={`${(scr.data.solvency.ratio * 100).toFixed(1)}%`}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Pipeline cards -- horizontal 3-column */}
      <div className={styles.pipelineSection}>
        <h2 className={styles.pipelineLabel}>{t('inicio.pipelineTitle')}</h2>
        <div className={styles.pipelineGrid}>
          <div className={styles.pipelineCard}>
            <h3 className={styles.pipelineCardTitle}>{t('inicio.mortalityPipeline')}</h3>
            <p className={styles.pipelineCardDesc}>{t('inicio.mortalityDesc')}</p>
            <DeepDiveLink text={t('inicio.viewMortality')} to="/mortalidad" />
          </div>
          <div className={styles.pipelineCard}>
            <h3 className={styles.pipelineCardTitle}>{t('inicio.pricing')}</h3>
            <p className={styles.pipelineCardDesc}>{t('inicio.pricingDesc')}</p>
            <DeepDiveLink text={t('inicio.calcPremiums')} to="/tarificacion" />
          </div>
          <div className={styles.pipelineCard}>
            <h3 className={styles.pipelineCardTitle}>{t('inicio.capitalReqs')}</h3>
            <p className={styles.pipelineCardDesc}>{t('inicio.capitalDesc')}</p>
            <DeepDiveLink text={t('inicio.viewSCR')} to="/scr" />
          </div>
        </div>
      </div>

      {/* k_t mini chart */}
      {lc.data && (
        <div className={styles.sectionBlockAccent} data-demo-section="hero">
          <h3 className={styles.sectionTitle}>{t('inicio.ktTrend')}</h3>
          <LineChart
            traces={[{
              x: lc.data.years,
              y: lc.data.kt,
              name: 'k_t',
              color: '#C41E3A',
            }]}
            xTitle={t('charts.year')}
            yTitle="k_t"
            height={300}
          />
        </div>
      )}

      {/* COVID Impact Teaser */}
      <div className={styles.covidTeaser}>
        <h3 className={styles.covidTeaserTitle}>{t('inicio.covidTeaser')}</h3>
        <p className={styles.covidTeaserDesc}>{t('inicio.covidTeaserDesc')}</p>
        <div className={styles.covidTeaserMetrics}>
          <MetricBlock label={t('inicio.covidTeaserDrift')} value="+0.22" unit={t('inicio.yearUnit')} />
          <MetricBlock label={t('inicio.covidTeaserPremium')} value="3-10%" />
        </div>
        <DeepDiveLink text={t('inicio.viewCovid')} to="/sensibilidad" />
      </div>
    </PageLayout>
  );
}
