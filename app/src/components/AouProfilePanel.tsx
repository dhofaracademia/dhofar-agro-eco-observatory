import ReadingExplanation from "./ReadingExplanation";
import { useTranslation } from "react-i18next";
import {
  aouIdFromFeature,
  dataQualityConfidence,
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
  const conf = dataQualityConfidence(p);
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

      <ReadingExplanation reading={p} />
      <details><summary className="cursor-pointer text-sm font-semibold text-crop-700">{t("simple.technicalDetails")}</summary>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
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
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">NDRE</dt>
          <dd>{p.ndre_available ? (p.ndre ?? "—") : "—"}</dd>
        </div>
        {typeof p.agricultural_probability === "number" && (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("analysis.colAgProb")}</dt>
            <dd>
              {p.agricultural_probability}{" "}
              <span className="text-xs text-sand-800/50">({p.ag_class ?? "—"})</span>
            </dd>
          </div>
        )}
        {typeof p.water_stress_score === "number" && (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("analysis.waterStress")}</dt>
            <dd>{p.water_stress_score}</dd>
          </div>
        )}
        {typeof p.vigor_stress_score === "number" && (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("analysis.vigorStress")}</dt>
            <dd>{p.vigor_stress_score}</dd>
          </div>
        )}
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
            {conf > 0 ? `${conf}%` : t("simple.qualityUnavailable")} <span className="text-xs text-sand-800/50">({t("aou.confidenceDataQuality")})</span>
          </dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-sand-800/50">{t("aou.date")}</dt>
          <dd>{p.date ?? "—"}</dd>
        </div>
      </dl>
      </details>

      {labels.noteKey && (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t(labels.noteKey)}
        </p>
      )}
      {(p.possible_biotic_stress || p.biotic_status === "possible") && (
        <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t("analysis.bioticPossible")}: {t("analysis.bioticDisclaimer")}
        </p>
      )}
      {!p.possible_biotic_stress &&
        p.biotic_status !== "possible" &&
        (p.biotic_status === "unknown" ||
          p.temporal_evidence_sufficient === false ||
          p.biotic_unknown_reason === "insufficient_temporal_evidence" ||
          (typeof p.n_clear_dates === "number" && p.n_clear_dates < 2)) && (
        <p className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t("analysis.temporalEvidenceInsufficient")}: {t("analysis.bioticUnknownTemporal")}
        </p>
      )}
      {p.assessability === "unassessable" && (
        <p className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t("analysis.unassessableBanner")}
        </p>
      )}
      {(p.observation_role === "retained_last_good" ||
        (p.refresh_status && p.refresh_status !== "refreshed")) && (
        <p className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t("analysis.observationRoleRetained", {
            role: String(p.observation_role || "retained_last_good"),
            status: String(p.refresh_status || "retained"),
          })}
        </p>
      )}
      {p.discovery_status === "provisional_new" && (
        <p className="mt-3 rounded-xl border border-violet-200 bg-violet-50 p-3 text-xs leading-relaxed text-sand-800/90">
          {t("analysis.discoveryProvisionalBanner")}
        </p>
      )}
    </aside>
  );
}
