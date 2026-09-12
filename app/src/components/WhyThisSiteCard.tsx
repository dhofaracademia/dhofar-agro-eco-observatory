import { useTranslation } from "react-i18next";

export type RestorationSiteProps = {
  id: string;
  name_en?: string;
  name_ar?: string;
  region?: string;
  suitability: number;
  confidence: number;
  mpi_class: string;
  action: string;
  species: string;
  species_note?: string;
  window: string;
  why: string[];
};

export default function WhyThisSiteCard({
  site,
  onClose,
}: {
  site: RestorationSiteProps | null;
  onClose?: () => void;
}) {
  const { t, i18n } = useTranslation();

  if (!site) {
    return (
      <aside className="rounded-2xl border border-dashed border-sand-300 bg-sand-50 p-5 text-sm text-sand-800/70">
        {t("restoration.selectHint")}
      </aside>
    );
  }

  const name = i18n.language === "ar" ? site.name_ar ?? site.name_en : site.name_en ?? site.name_ar;

  return (
    <aside className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
            {t("mountainStatus.siteStatus")}
          </div>
          <h3 className="font-mono text-lg font-bold text-crop-700">{site.id}</h3>
          {name && <p className="mt-1 text-sm text-sand-800/80">{name}</p>}
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-sand-300 px-2 py-0.5 text-xs text-sand-800 hover:bg-sand-100"
          >
            {t("aou.close")}
          </button>
        )}
      </div>

      <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-earth-600">
        {t("mountainStatus.productKind")}
      </p>
      <p className="mb-3 rounded-lg border border-sand-200 bg-sand-50 px-3 py-2 text-xs text-sand-900">
        {t("mountainStatus.noPlantHere")}
      </p>

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-crop-600/30 bg-crop-600/5 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
            {t("restoration.suitability")}
          </div>
          <div className="text-2xl font-bold text-crop-700">{site.suitability}</div>
          <p className="mt-1 text-[11px] text-sand-800/60">{t("restoration.suitabilityHint")}</p>
        </div>
        <div className="rounded-xl border border-sand-300 bg-sand-50 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
            {t("restoration.confidence")}
          </div>
          <div className="text-2xl font-bold text-sand-900">{site.confidence}</div>
          <p className="mt-1 text-[11px] text-sand-800/60">{t("restoration.confidenceHint")}</p>
        </div>
      </div>

      <p className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-earth-600">
        {t("restoration.suitabilityNeqConfidence")}
      </p>

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("restoration.mpi")}</dt>
          <dd>
            {site.mpi_class}
            <span className="mt-1 block text-[11px] font-medium text-earth-600">
              {t("mountainStatus.productKind")}
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
            {t("mountainStatus.timingLabel")}
          </dt>
          <dd>{t("mountainStatus.timingDeferred")}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
            {t("mountainStatus.seedingHold")}
          </dt>
          <dd className="text-xs text-sand-800/80">{t("mountainStatus.actionHidden")}</dd>
        </div>
      </dl>

      <div className="mt-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sand-800/50">
          {t("restoration.reasons")}
        </h4>
        <ul className="list-disc space-y-1 ps-5 text-sm text-sand-800/90">
          {(site.why ?? []).map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
