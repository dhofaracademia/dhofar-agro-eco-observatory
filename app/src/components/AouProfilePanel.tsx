import { useTranslation } from "react-i18next";
import {
  aouIdFromFeature,
  confidenceStub,
  estimatedAreaHa,
  featureCentroid,
  mapAlertLabels,
  type AouFeature,
} from "../lib/aou";

export default function AouProfilePanel({
  feature,
  onClose,
}: {
  feature: AouFeature | null;
  onClose?: () => void;
}) {
  const { t } = useTranslation();
  if (!feature) {
    return (
      <aside className="rounded-2xl border border-dashed border-sand-300 bg-sand-50 p-5 text-sm text-sand-800/70">
        {t("aou.selectHint")}
      </aside>
    );
  }

  const p = feature.properties;
  const id = aouIdFromFeature(feature);
  const { lon, lat } = featureCentroid(feature);
  const area = estimatedAreaHa(p);
  const conf = confidenceStub(p);
  const labels = mapAlertLabels(p.alert);

  return (
    <aside className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">
            {t("aou.profileTitle")}
          </div>
          <h3 className="font-mono text-lg font-bold text-crop-700">{id}</h3>
          <p className="mt-1 text-xs text-sand-800/60">{t("aou.notOfficialFarm")}</p>
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

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.area")}</dt>
          <dd>{area.toFixed(2)} ha <span className="text-xs text-sand-800/50">({t("aou.estimated")})</span></dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.coords")}</dt>
          <dd className="font-mono text-xs">{lat.toFixed(4)}°, {lon.toFixed(4)}°</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">NDVI</dt>
          <dd>{p.ndvi ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">NDMI</dt>
          <dd>{p.ndmi ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.vegetationHealth")}</dt>
          <dd>{t(labels.healthKey)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.waterStress")}</dt>
          <dd>{t(labels.waterKey)}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.confidence")}</dt>
          <dd>
            {conf}% <span className="text-xs text-sand-800/50">({t("aou.confidenceStub")})</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.date")}</dt>
          <dd>{p.date ?? "—"}</dd>
        </div>
      </dl>

      {labels.noteKey && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t(labels.noteKey)}
        </p>
      )}
    </aside>
  );
}
