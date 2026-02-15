import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import SliderInput from './SliderInput';
import styles from './PremiumForm.module.css';

export interface PremiumRequest {
  product_type: string;
  age: number;
  sum_assured: number;
  term?: number;
  interest_rate: number;
}

interface PremiumFormProps {
  onSubmit: (req: PremiumRequest) => void;
  loading: boolean;
}

export default function PremiumForm({ onSubmit, loading }: PremiumFormProps) {
  const { t } = useTranslation();
  const [productType, setProductType] = useState('whole_life');
  const [age, setAge] = useState(30);
  const [sumAssured, setSumAssured] = useState(1000000);
  const [term, setTerm] = useState(20);
  const [interestRate, setInterestRate] = useState(0.05);

  const needsTerm = productType === 'term' || productType === 'endowment';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      product_type: productType,
      age,
      sum_assured: sumAssured,
      term: needsTerm ? term : undefined,
      interest_rate: interestRate,
    });
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.product')}</label>
        <select
          className={styles.select}
          value={productType}
          onChange={(e) => setProductType(e.target.value)}
        >
          <option value="whole_life">{t('forms.wholeLife')}</option>
          <option value="term">{t('forms.termLife')}</option>
          <option value="endowment">{t('forms.endowment')}</option>
        </select>
      </div>

      <SliderInput
        label={t('forms.age')}
        min={20}
        max={70}
        step={1}
        value={age}
        onChange={setAge}
        unit={t('forms.years')}
      />

      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.sumAssured')}</label>
        <input
          type="number"
          className={styles.input}
          value={sumAssured}
          onChange={(e) => setSumAssured(Number(e.target.value))}
          min={10000}
          step={10000}
        />
      </div>

      {needsTerm && (
        <SliderInput
          label={t('forms.term')}
          min={5}
          max={40}
          step={1}
          value={term}
          onChange={setTerm}
          unit={t('forms.years')}
        />
      )}

      <SliderInput
        label={t('forms.interestRate')}
        min={0.01}
        max={0.10}
        step={0.005}
        value={interestRate}
        onChange={setInterestRate}
        formatValue={(v: number) => `${(v * 100).toFixed(1)}%`}
      />

      <button type="submit" className={styles.submitBtn} disabled={loading}>
        {loading ? t('forms.calculating') : t('forms.calculate')}
      </button>
    </form>
  );
}
