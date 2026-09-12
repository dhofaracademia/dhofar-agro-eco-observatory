import { useTranslation } from "react-i18next";

export type RestorationSiteProps = {
  id: string;
  name_en?: string;
  name_ar?: string;
  region?: string;
  suitability?: number | null;
  confidence?: number | null;
  mpi_class?: string | null;
  action?: string | null;
  species?: string;
  species_note?: string;
  window?: string | null;
  why?: string[];
  product_kind?: string;
  timing?: string;
  seeding_recommendation?: string;
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
  const statusWhy = [
    t("mountainStatus.productKind"),
    t("mountainStatus.timingDeferred"),
    t("mountainStatus.seedingHold"),
    t("mountainStatus.noPlantHere"),
  ];

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

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("restoration.mpi")}</dt>
          <dd>
            {t("mountainStatus.mpiOnsetProvisional")}
            <span className="mt-1 block text-[11px] font-medium text-earth-600">
              {site.product_kind || "onset_window_dry_mpi_provisional"}
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
        {site.species && (
          <div className="sm:col-span-2">
            <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
              {t("mountainStatus.fogCatalogList")}
            </dt>
            <dd className="text-xs text-sand-800/80">
              {site.species}
              {site.species_note ? ` — ${site.species_note}` : ""}
            </dd>
          </div>
        )}
      </dl>

      <div className="mt-4">
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-sand-800/50">
          {t("mountainStatus.statusNotes")}
        </h4>
        <ul className="list-disc space-y-1 ps-5 text-sm text-sand-800/90">
          {statusWhy.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
