import { useTranslation } from 'react-i18next';
import type { AouAlertProps } from '../lib/aou';

export default function ReadingExplanation({ reading }: { reading: Partial<AouAlertProps> }) {
  const { t } = useTranslation();
  const rejected = reading.assessability === 'unassessable' || reading.observation_role === 'retained_last_good';
  const known = ['healthy', 'bare', 'water_attention', 'vigor_attention'];
  const state = rejected || !known.includes(reading.alert || '') ? 'unclear' : reading.alert;
  return (
    <div className="my-4 rounded-xl border border-sand-200 bg-sand-50 p-4">
      <h3 className="font-semibold text-crop-700">{t('simple.whatItMeans')}</h3>
      <p className="mt-2 text-sm leading-relaxed">{t(`simple.readings.${state}`)}</p>
      <p className="mt-2 text-sm leading-relaxed"><strong>{t('simple.nextStep')} </strong>{t(`simple.actions.${state}`)}</p>
      {(reading.n_clear_dates ?? 0) < 2 && <p className="mt-2 text-sm text-amber-950">{t('simple.shortHistory')}</p>}
      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-medium">{t('simple.explainNumbers')}</summary>
        <dl className="mt-3 space-y-3">
          {['ndvi', 'ndmi', 'confidence'].map((key) => <div key={key}><dt className="font-semibold">{t(`simple.terms.${key}.title`)}</dt><dd className="mt-1 leading-relaxed">{t(`simple.terms.${key}.body`)}</dd></div>)}
        </dl>
      </details>
    </div>
  );
}
