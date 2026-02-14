import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import PageLayout from '../components/layout/PageLayout';
import MetricBlock from '../components/data/MetricBlock';
import DeepDiveLink from '../components/data/DeepDiveLink';
import LineChart from '../components/charts/LineChart';
import LoadingState from '../components/common/LoadingState';
import { useGet, usePost } from '../hooks/useApi';
import type { LeeCaterFitResponse, SCRResponse } from '../types';
import styles from './Inicio.module.css';

export default function Inicio() {
  const { t } = useTranslation();
  const lc = useGet<LeeCaterFitResponse>('/mortality/lee-carter');
  const scr = usePost<object, SCRResponse>('/scr/compute');

  useEffect(() => {
    lc.execute();
    scr.execute({ available_capital: 1_000_000 });
  }, []);

  return (
    <PageLayout>
      {/* Hero split layout */}
      <div className={styles.hero}>
        <div className={styles.heroLeft}>
          <h1 className={styles.projectTitle}>{t('inicio.title')}</h1>
          <p className={styles.projectDesc}>{t('inicio.desc')}</p>

          <div className={styles.statGrid}>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>12</div>
              <div className={styles.statLabel}>{t('inicio.modules')}</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>169</div>
              <div className={styles.statLabel}>{t('inicio.tests')}</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>4</div>
              <div className={styles.statLabel}>{t('inicio.products')}</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statNumber}>4</div>
              <div className={styles.statLabel}>{t('inicio.scrModules')}</div>
            </div>
          </div>
        </div>

        <div className={styles.heroRight}>
          <div className={styles.liveLabel}>{t('inicio.liveMetrics')}</div>

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

      {/* k_t mini chart */}
      {lc.data && (
        <div className={styles.sectionBlock}>
          <h3 className={styles.sectionTitle}>{t('inicio.ktTrend')}</h3>
          <LineChart
            traces={[{
              x: lc.data.years,
              y: lc.data.kt,
              name: 'k_t',
              color: '#C41E3A',
            }]}
            xTitle="Año"
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
          <MetricBlock label={t('inicio.covidTeaserDrift')} value="+0.22" unit="/año" />
          <MetricBlock label={t('inicio.covidTeaserPremium')} value="3-10%" />
        </div>
        <DeepDiveLink text={t('inicio.viewCovid')} to="/sensibilidad" />
      </div>

      {/* Navigation sections */}
      <div className={styles.sectionBlock}>
        <h2 className={styles.sectionTitle}>{t('inicio.mortalityPipeline')}</h2>
        <p className={styles.sectionDesc}>{t('inicio.mortalityDesc')}</p>
        <DeepDiveLink text={t('inicio.viewMortality')} to="/mortalidad" />
      </div>

      <div className={styles.sectionBlock}>
        <h2 className={styles.sectionTitle}>{t('inicio.pricing')}</h2>
        <p className={styles.sectionDesc}>{t('inicio.pricingDesc')}</p>
        <DeepDiveLink text={t('inicio.calcPremiums')} to="/tarificacion" />
      </div>

      <div className={styles.sectionBlock}>
        <h2 className={styles.sectionTitle}>{t('inicio.capitalReqs')}</h2>
        <p className={styles.sectionDesc}>{t('inicio.capitalDesc')}</p>
        <DeepDiveLink text={t('inicio.viewSCR')} to="/scr" />
      </div>
    </PageLayout>
  );
}
