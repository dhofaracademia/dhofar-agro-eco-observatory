import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Guide() {
  const { t } = useTranslation();
  const { locale = 'en' } = useParams();
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <header><p className="text-sm font-semibold text-crop-700">{t('simple.noExpertise')}</p><h1 className="mt-2 text-3xl font-bold">{t('simple.guideTitle')}</h1><p className="mt-3 leading-relaxed">{t('simple.guideIntro')}</p></header>
      <ol className="grid gap-4 sm:grid-cols-3">
        {['choose', 'read', 'act'].map((step, index) => <li key={step} className="rounded-2xl border border-sand-200 bg-white p-5"><span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-crop-600 text-white">{index + 1}</span><h2 className="mt-3 font-semibold">{t(`simple.steps.${step}.title`)}</h2><p className="mt-2 text-sm leading-relaxed">{t(`simple.steps.${step}.body`)}</p></li>)}
      </ol>
      <Link className="inline-block rounded-full bg-crop-600 px-6 py-3 font-semibold text-white" to={`/${locale}/map`}>{t('simple.startMap')}</Link>
      <section><h2 className="mb-4 text-xl font-semibold">{t('simple.colours')}</h2><div className="grid gap-3 sm:grid-cols-2">{['healthy', 'water_attention', 'vigor_attention', 'bare', 'unclear'].map(key => <article key={key} className="rounded-xl border border-sand-200 bg-white p-4"><h3 className="font-semibold">{t(`simple.labels.${key}`)}</h3><p className="mt-2 text-sm leading-relaxed">{t(`simple.readings.${key}`)}</p></article>)}</div></section>
      <section><h2 className="mb-3 text-xl font-semibold">{t('simple.commonQuestions')}</h2><div className="space-y-3">{['aou', 'ndvi', 'ndmi', 'confidence', 'missing', 'updates', 'pests', 'mountains'].map(key => <details key={key} className="rounded-xl border border-sand-200 bg-white p-4"><summary className="cursor-pointer font-semibold">{t(`simple.terms.${key}.title`)}</summary><p className="mt-3 text-sm leading-relaxed">{t(`simple.terms.${key}.body`)}</p></details>)}</div></section>
    </div>
  );
}
