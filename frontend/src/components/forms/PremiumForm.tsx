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
  sex: 'male' | 'female' | 'unisex';
}

interface PremiumFormProps {
  onSubmit: (req: PremiumRequest) => void;
  loading: boolean;
}

export default function PremiumForm({ onSubmit, loading }: PremiumFormProps) {
  const { t } = useTranslation();
  const [productType, setProductType] = useState('whole_life');
  const [sex, setSex] = useState<'male' | 'female' | 'unisex'>('male');
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
      sex,
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
        <span className={styles.hint}>{t('hints.product')}</span>
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.sex')}</label>
        <select
          className={styles.select}
          value={sex}
          onChange={(e) => setSex(e.target.value as 'male' | 'female' | 'unisex')}
        >
          <option value="male">{t('forms.male')}</option>
          <option value="female">{t('forms.female')}</option>
          <option value="unisex">{t('forms.unisex')}</option>
        </select>
        <span className={styles.hint}>{t('hints.sex')}</span>
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
        <span className={styles.hint}>{t('hints.sumAssured')}</span>
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
