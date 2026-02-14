import { useTranslation } from 'react-i18next';
import FormulaBlock from '../components/data/FormulaBlock';
import MetricBlock from '../components/data/MetricBlock';
import DeepDiveLink from '../components/data/DeepDiveLink';
import styles from './Metodologia.module.css';

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

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.headerTitle}>{t('metodologia.title')}</h1>
        <p className={styles.headerSubtitle}>{t('metodologia.subtitle')}</p>
      </header>

      {/* SECTION 1: DATOS */}
      <Section number="01" title={t('metodologia.sections.datos')}>
        <p className={styles.narrative}>
          Empecé con los datos crudos de mortalidad del INEGI: 30 años de defunciones registradas
          en México (1990-2019), cruzados con las proyecciones de población del CONAPO para obtener
          exposiciones. Para cada edad <em>x</em> y año <em>t</em>, calculé la tasa central de
          mortalidad dividiendo las defunciones observadas entre la población expuesta al riesgo.
          Estos datos cubren edades de 0 a 100 años, con todas las particularidades de la experiencia
          mexicana: la mortalidad infantil elevada, el pico de mortalidad en jóvenes adultos por
          causas externas, y el crecimiento exponencial en edades avanzadas siguiendo un patrón
          tipo Gompertz.
        </p>
        <FormulaBlock
          latex="m_{x,t} = \\frac{D_{x,t}}{E_{x,t}}"
          label={t('metodologia.formulaLabels.centralDeathRate')}
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
          Los datos crudos de mortalidad contienen ruido estadístico considerable: fluctuaciones
          aleatorias año con año, especialmente en edades con pocas observaciones. Necesitaba un
          método que suavizara este ruido sin destruir la señal biológica subyacente. Utilicé la
          graduación Whittaker-Henderson, que resuelve un problema de optimización elegante:
          minimizar simultáneamente la infidelidad a los datos observados y la rugosidad de la curva
          graduada. El parámetro <span className={styles.highlight}>lambda = 10^5</span> controla
          el balance entre fidelidad y suavidad. Cuando lambda tiende a cero, la curva graduada
          reproduce exactamente los datos crudos; cuando lambda crece, la curva se acerca a un
          polinomio de grado z-1. La solución es un sistema lineal simétrico definido positivo con
          estructura de banda, lo que permite resolverlo en tiempo O(n).
        </p>
        <FormulaBlock
          latex="\\hat{g} = \\left(W + \\lambda D'D\\right)^{-1} W \\, m"
          label={t('metodologia.formulaLabels.graduation')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label="Lambda" value="100,000" />
          <MetricBlock label={t('metodologia.metrics.differenceOrder')} value="3" />
          <MetricBlock label={t('metodologia.metrics.weights')} value={t('metodologia.metrics.exposures')} />
        </div>
      </Section>

      {/* SECTION 3: LEE-CARTER */}
      <Section number="03" title={t('metodologia.sections.leeCarter')}>
        <p className={styles.narrative}>
          Con las tasas ya graduadas, apliqué el modelo Lee-Carter para descomponer la mortalidad
          en un perfil por edad y una tendencia temporal. La idea central es que el logaritmo de la
          tasa de mortalidad se puede expresar como una combinación de tres componentes: un nivel
          promedio <em>a_x</em> (que captura la forma de la curva por edad), una sensibilidad al
          cambio <em>b_x</em> (que mide cuánto mejora cada edad), y un índice temporal <em>k_t</em>
          (que captura la mejora general). Resolví el sistema por SVD (descomposición en valores
          singulares) con las restricciones de identificabilidad: la suma de b_x igual a 1 y la
          suma de k_t igual a 0. Para México, el primer componente singular explica el{' '}
          <span className={styles.highlight}>77.7%</span> de la variabilidad -- menor que para
          España (94.8%) o Estados Unidos (86.7%), reflejando mayor heterogeneidad en la experiencia
          mexicana.
        </p>
        <FormulaBlock
          latex="\\ln(m_{x,t}) = a_x + b_x \\cdot k_t + \\varepsilon_{x,t}"
          label={t('metodologia.formulaLabels.leeCarter')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.explainedVar')} value="77.7%" />
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
          Una vez estimado el modelo, el siguiente paso fue proyectar la mortalidad hacia el futuro.
          El índice temporal k_t sigue una caminata aleatoria con deriva (Random Walk with Drift),
          donde la deriva representa la velocidad promedio de mejora de la mortalidad. Para México
          pre-COVID, la deriva fue de <span className={styles.highlight}>-1.076 por año</span>,
          indicando una mejora sostenida pero más lenta que en España (-2.895) o Estados Unidos (-1.192).
          Lo que descubrí al incluir los datos 2020-2024 fue revelador: el COVID-19 redujo la
          deriva a -0.855, lo que se traduce en primas entre 3% y 10% más altas dependiendo del
          producto y la edad. La proyección central con banda de confianza al 95% permite construir
          tablas de mortalidad proyectadas que alimentan al motor de tarificación.
        </p>
        <FormulaBlock
          latex="k_{t+1} = k_t + d + \\sigma\\, Z_t, \\quad Z_t \\sim N(0,1)"
          label={t('metodologia.formulaLabels.rwd')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.driftMexico')} value="-1.076" unit={t('metodologia.metrics.perYear')} />
          <MetricBlock label={t('metodologia.metrics.driftSpain')} value="-2.895" unit={t('metodologia.metrics.perYear')} />
          <MetricBlock label={t('metodologia.metrics.driftUSA')} value="-1.192" unit={t('metodologia.metrics.perYear')} />
        </div>
      </Section>

      {/* SECTION 5: TARIFICACION */}
      <Section number="05" title={t('metodologia.sections.tarificacion')}>
        <p className={styles.narrative}>
          Con la tabla de mortalidad proyectada, construí funciones de conmutación (D_x, N_x, C_x, M_x)
          que condensan toda la información de mortalidad y descuento en cantidades que simplifican
          el cálculo de primas. La tarificación sigue el principio de equivalencia: la prima es el
          precio justo tal que el valor presente esperado de lo que paga el asegurado iguala al valor
          presente esperado de lo que recibirá. El resultado más sorprendente del análisis de
          sensibilidad fue que la <span className={styles.highlight}>tasa de interés es el factor
          dominante</span>: una vida entera a edad 40 tiene una prima de $17,910 al 2% pero solo
          $7,014 al 8% -- un rango de 101%. En contraste, un choque de +30% en mortalidad solo
          aumenta la prima un 16.2%.
        </p>
        <FormulaBlock
          latex="P = SA \\cdot \\frac{M_x}{N_x}"
          label={t('metodologia.formulaLabels.wholeLifePremium')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.premiumAge40')} value="$10,765" />
          <MetricBlock label={t('metodologia.metrics.rateSpread')} value="101%" />
          <MetricBlock label={t('metodologia.metrics.mortalityImpact')} value="+16.2%" />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.calculatePremiums')} to="/tarificacion" />
        </div>
      </Section>

      {/* SECTION 6: RESERVAS */}
      <Section number="06" title={t('metodologia.sections.reservas')}>
        <p className={styles.narrative}>
          Las reservas existen porque cobramos primas niveladas pero la mortalidad crece con la edad.
          En los primeros años la prima excede el costo real del riesgo, generando un excedente que
          se acumula. En los años posteriores, cuando la mortalidad supera la prima, ese excedente
          cubre el déficit. Utilicé el método prospectivo: la reserva al tiempo t es el valor presente
          de las obligaciones futuras menos el valor presente de las primas futuras por cobrar. Lo
          crucial para el marco de Solvencia II es que esta reserva prospectiva es exactamente la{' '}
          <span className={styles.highlight}>Mejor Estimación (BEL)</span> de la obligación. No fue
          necesario inventar matemáticas nuevas: la reserva actuarial clásica, calculada con supuestos
          de mejor estimación, es la BEL que exige la regulación de la CNSF.
        </p>
        <FormulaBlock
          latex="{}_tV = SA \\cdot A_{x+t} - P \\cdot \\ddot{a}_{x+t}"
          label={t('metodologia.formulaLabels.prospectiveReserve')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.belTotal')} value="$5.16M" />
          <MetricBlock label={t('metodologia.metrics.belAnnuity')} value="$4.27M" unit="(83%)" />
          <MetricBlock label={t('metodologia.metrics.belDeath')} value="$0.89M" unit="(17%)" />
        </div>
        <div className={styles.linkRow}>
          <DeepDiveLink text={t('metodologia.links.seePricing')} to="/tarificacion" />
        </div>
      </Section>

      {/* SECTION 7: RCS */}
      <Section number="07" title={t('metodologia.sections.rcs')}>
        <p className={styles.narrative}>
          El Requerimiento de Capital de Solvencia (RCS) es el colchón que una aseguradora debe
          mantener para sobrevivir un escenario adverso de 1 en 200 años (VaR al 99.5%). Implementé
          cuatro módulos de riesgo siguiendo el marco de Solvencia II adaptado por la CNSF:
          mortalidad (+15% permanente en q_x), longevidad (-20% permanente en q_x), tasa de interés
          (+/- 1% paralelo), y catástrofe (+35% puntual, calibrado con la experiencia COVID-19
          mexicana). La agregación usa una matriz de correlación que captura las coberturas naturales
          del portafolio -- la correlación negativa de -0.25 entre mortalidad y longevidad genera un{' '}
          <span className={styles.highlight}>beneficio por diversificación del 14.4%</span>. El
          resultado: un RCS total de $568,700 sobre provisiones técnicas de $5.51M. El riesgo de
          tasa de interés domina con el 79.7% del capital requerido, porque afecta a todas las
          pólizas del portafolio.
        </p>
        <FormulaBlock
          latex="RCS = \\sqrt{\\vec{S}^{\\,T} \\cdot C \\cdot \\vec{S}}"
          label={t('metodologia.formulaLabels.scrAggregation')}
        />
        <div className={styles.metricsRow}>
          <MetricBlock label={t('metodologia.metrics.totalSCR')} value="$568,700" />
          <MetricBlock label={t('metodologia.metrics.techProvisions')} value="$5.51M" />
          <MetricBlock label={t('metodologia.metrics.diversification')} value="14.4%" />
          <MetricBlock label={t('metodologia.metrics.dominantRisk')} value={t('metodologia.metrics.interestRateRisk')} />
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
        <div style={{ display: 'grid', gap: '16px', maxWidth: '600px' }}>
          <div style={{ padding: '16px', border: '1px solid #E0E0E0' }}>
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>{t('metodologia.latexDoc')}</div>
            <div style={{ color: '#9E9E9E', fontSize: '0.875rem' }}>docs/lee_carter_reestimation.pdf</div>
          </div>
          <div style={{ padding: '16px', border: '1px solid #E0E0E0' }}>
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>{t('metodologia.techDocs')}</div>
            <div style={{ color: '#9E9E9E', fontSize: '0.875rem' }}>{t('metodologia.docPairsDesc')}</div>
          </div>
        </div>
      </Section>
    </main>
  );
}
