import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import styles from './PremiumForm.module.css';

export interface PolicyData {
  policy_id: string;
  product_type: string;
  issue_age: number;
  sum_assured: number;
  annual_pension: number;
  term?: number;
  duration: number;
}

interface PolicyFormProps {
  onSubmit: (policy: PolicyData) => void;
  loading: boolean;
}

export default function PolicyForm({ onSubmit, loading }: PolicyFormProps) {
  const { t } = useTranslation();
  const [policyId, setPolicyId] = useState('');
  const [productType, setProductType] = useState('whole_life');
  const [issueAge, setIssueAge] = useState(30);
  const [sumAssured, setSumAssured] = useState(1000000);
  const [annualPension, setAnnualPension] = useState(120000);
  const [term, setTerm] = useState(20);
  const [duration, setDuration] = useState(0);

  const isDeath = ['whole_life', 'term', 'endowment'].includes(productType);
  const isAnnuity = productType === 'annuity';
  const needsTerm = productType === 'term' || productType === 'endowment';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      policy_id: policyId,
      product_type: productType,
      issue_age: issueAge,
      sum_assured: isDeath ? sumAssured : 0,
      annual_pension: isAnnuity ? annualPension : 0,
      term: needsTerm ? term : undefined,
      duration,
    });
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.policyId')}</label>
        <input
          type="text"
          className={styles.input}
          value={policyId}
          onChange={(e) => setPolicyId(e.target.value)}
          placeholder="P001"
        />
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.productType')}</label>
        <select
          className={styles.select}
          value={productType}
          onChange={(e) => setProductType(e.target.value)}
        >
          <option value="whole_life">{t('forms.wholeLife')}</option>
          <option value="term">{t('forms.termLife')}</option>
          <option value="endowment">{t('forms.endowment')}</option>
          <option value="annuity">{t('forms.lifeAnnuity')}</option>
        </select>
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.issueAge')}</label>
        <input
          type="number"
          className={styles.input}
          value={issueAge}
          onChange={(e) => setIssueAge(Number(e.target.value))}
          min={20}
          max={80}
        />
      </div>

      {isDeath && (
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
      )}

      {isAnnuity && (
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{t('forms.annualPension')}</label>
          <input
            type="number"
            className={styles.input}
            value={annualPension}
            onChange={(e) => setAnnualPension(Number(e.target.value))}
            min={10000}
            step={10000}
          />
        </div>
      )}

      {needsTerm && (
        <div className={styles.fieldGroup}>
          <label className={styles.label}>{t('forms.term')} ({t('forms.years')})</label>
          <input
            type="number"
            className={styles.input}
            value={term}
            onChange={(e) => setTerm(Number(e.target.value))}
            min={5}
            max={40}
          />
        </div>
      )}

      <div className={styles.fieldGroup}>
        <label className={styles.label}>{t('forms.duration')} ({t('forms.years')})</label>
        <input
          type="number"
          className={styles.input}
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          min={0}
          max={50}
        />
      </div>

      <button type="submit" className={styles.submitBtn} disabled={loading}>
        {loading ? t('forms.adding') : t('forms.addPolicy')}
      </button>
    </form>
  );
}
