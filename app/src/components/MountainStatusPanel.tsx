import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { publicUrl } from "../lib/publicUrl";
import SeedCatalogPanel from "./SeedCatalogPanel";

type StatusProps = {
  id?: string;
  segment_id: string;
  name_en?: string;
  name_ar?: string;
  khareef_stage?: string;
  product_kind?: string;
  ndvi?: number | null;
  ndmi?: number | null;
  n_clear?: number;
  data_quality?: string;
  evidence_level?: string;
  optional_segment?: boolean;
};

type StatusFC = {
  type: "FeatureCollection";
  features: { type: "Feature"; properties: StatusProps }[];
  properties?: {
    note_en?: string;
    note_ar?: string;
    khareef_stage?: string;
    product_kind?: string;
    product_stamp?: string;
    seeding_recommendation?: string;
  };
  asof_date?: string;
};

const STAGE_CHIP: Record<string, string> = {
  pre_khareef: "border-sand-300 bg-sand-50 text-sand-900",
  onset: "border-sky-300 bg-sky-50 text-sky-950",
  peak: "border-emerald-300 bg-emerald-50 text-emerald-950",
  late_khareef: "border-amber-300 bg-amber-50 text-amber-950",
  post_khareef: "border-violet-300 bg-violet-50 text-violet-950",
  insufficient: "border-stone-400 bg-stone-100 text-stone-800",
};

export default function MountainStatusPanel() {
  const { t, i18n } = useTranslation();
  const ar = i18n.language?.startsWith("ar");
  const [data, setData] = useState<StatusFC | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(publicUrl("data/mountain/khareef_status_cells.geojson"))
      .then((r) => {
        if (!r.ok) throw new Error("status cells");
        return r.json();
      })
      .then((j: StatusFC) => {
        if (!cancelled) setData(j);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const features = useMemo(() => data?.features ?? [], [data]);
  const corridorStage = data?.properties?.khareef_stage ?? "insufficient";
  const corridorPk = data?.properties?.product_kind ?? "insufficient";

  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-amber-400 bg-amber-50 p-4 text-sm text-amber-950">
        <p className="font-semibold">{t("khareefStatus.banner")}</p>
        <p className="mt-2 text-xs">{t("khareefStatus.bannerHelp")}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-semibold uppercase tracking-wide">
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("khareefStatus.productStamp")}
          </span>
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5">
            {t("mountainStatus.timingDeferred")}
          </span>
          <span className="rounded-full border border-sand-400 bg-white px-2 py-0.5 text-sand-900">
            {t("mountainStatus.seedingHold")}
          </span>
          <span className={`rounded-full border px-2 py-0.5 ${STAGE_CHIP[corridorStage] ?? STAGE_CHIP.insufficient}`}>
            {t(`khareefStatus.stages.${corridorStage}`, { defaultValue: corridorStage })}
          </span>
          <span className="rounded-full border border-amber-400 bg-white px-2 py-0.5 normal-case">
            {corridorPk}
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-sand-200 bg-white p-4 shadow-sm">
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold text-crop-700">{t("khareefStatus.corridorTitle")}</h3>
          {data?.asof_date && (
            <span className="text-[10px] text-sand-800/60">
              {t("khareefStatus.asof")}: {data.asof_date}
            </span>
          )}
        </div>
        <p className="mb-3 text-xs text-sand-800/80">
          {ar ? data?.properties?.note_ar : data?.properties?.note_en}
        </p>
        {error && <p className="text-xs text-red-700">{t("khareefStatus.loadError")}</p>}
        {!data && !error && <p className="text-xs text-sand-800/60">{t("khareefStatus.loading")}</p>}
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => {
            const p = f.properties;
            const name = ar ? p.name_ar ?? p.name_en : p.name_en ?? p.name_ar;
            const stage = p.khareef_stage ?? "insufficient";
            return (
              <div
                key={p.segment_id}
                className="rounded-xl border border-sand-200 bg-sand-50/80 p-3 text-xs"
              >
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-semibold text-sand-900">{name}</span>
                  {p.optional_segment && (
                    <span className="rounded-full border border-sand-300 px-1.5 py-0.5 text-[9px] uppercase text-sand-700">
                      {t("khareefStatus.optional")}
                    </span>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${STAGE_CHIP[stage] ?? STAGE_CHIP.insufficient}`}>
                    {t(`khareefStatus.stages.${stage}`, { defaultValue: stage })}
                  </span>
                  <span className="rounded-full border border-sand-300 bg-white px-2 py-0.5 text-[10px]">
                    {p.product_kind ?? "insufficient"}
                  </span>
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-[10px] text-sand-800/80">
                  <dt>NDVI</dt>
                  <dd>{p.ndvi == null ? t("khareefStatus.nullProxy") : p.ndvi.toFixed(3)}</dd>
                  <dt>NDMI</dt>
                  <dd>{p.ndmi == null ? t("khareefStatus.nullProxy") : p.ndmi.toFixed(3)}</dd>
                  <dt>{t("khareefStatus.nClear")}</dt>
                  <dd>{p.n_clear ?? 0}</dd>
                  <dt>{t("khareefStatus.evidence")}</dt>
                  <dd className="truncate" title={p.evidence_level}>
                    {p.evidence_level ?? "—"}
                  </dd>
                </dl>
                {p.data_quality && (
                  <p className="mt-1 text-[10px] text-sand-800/60">{p.data_quality}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <p className="text-xs text-sand-800/70">{t("mountainStatus.noPlantHere")}</p>
      <SeedCatalogPanel domain="fog_escarpment" />
    </div>
  );
}
