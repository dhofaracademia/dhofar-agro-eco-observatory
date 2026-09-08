import { useTranslation } from "react-i18next";

export default function About() {
  const { t } = useTranslation();
  const steps = t("about.workflow", { returnObjects: true }) as string[];
  const honesty = t("about.honesty", { returnObjects: true }) as string[];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("about.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("about.blurb")}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
          <h2 className="mb-2 font-semibold text-crop-700">{t("about.aoiTitle")}</h2>
          <p className="text-sm leading-relaxed text-sand-800/90">{t("about.aoiBody")}</p>
        </section>
        <section className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
          <h2 className="mb-2 font-semibold text-crop-700">{t("about.sensorsTitle")}</h2>
          <p className="text-sm leading-relaxed text-sand-800/90">{t("about.sensorsBody")}</p>
        </section>
      </div>

      <section className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-semibold text-crop-700">{t("about.workflowTitle")}</h2>
        <ol className="list-decimal space-y-2 ps-5 text-sm text-sand-800/90">
          {Array.isArray(steps) && steps.map((s) => <li key={s}>{s}</li>)}
        </ol>
      </section>

      <section className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-semibold text-crop-700">{t("about.honestyTitle")}</h2>
        <ul className="list-disc space-y-2 ps-5 text-sm text-sand-800/90">
          {Array.isArray(honesty) && honesty.map((s) => <li key={s}>{s}</li>)}
        </ul>
      </section>

      <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <h2 className="mb-2 font-semibold text-earth-600">{t("about.limitTitle")}</h2>
        <p className="text-sm leading-relaxed text-sand-800/90">{t("about.limitBody")}</p>
      </section>
    </div>
  );
}
