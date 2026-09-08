import { useState } from "react";
import { useTranslation } from "react-i18next";
import AlertMap from "../components/AlertMap";
import RestorationMap from "../components/RestorationMap";
import ObservatoryModeToggle from "../components/ObservatoryModeToggle";
import KhareefCalendar from "../components/KhareefCalendar";
import AouOfflineBadge from "../components/AouOfflineBadge";
import NajdSeasonalChip from "../components/NajdSeasonalChip";
import hubsData from "../data/hubs.json";
import type { ObservatoryMode } from "../lib/mode";

export default function MapPage() {
  const { t, i18n } = useTranslation();
  const { hubs, bbox } = hubsData;
  const [mode, setMode] = useState<ObservatoryMode>("agricultural");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("map.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("map.blurb")}</p>
      </div>

      <ObservatoryModeToggle mode={mode} onChange={setMode} />
      <KhareefCalendar active="peak" />

      {mode === "agricultural" ? (
        <section className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-crop-700">{t("map.liveTitle")}</h2>
            <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-950">
              {t("provisional.badge")}
            </span>
            <AouOfflineBadge showHelper={false} />
            <NajdSeasonalChip compact />
          </div>
          <p className="text-sm text-sand-800/90">{t("map.liveBlurb")}</p>
          <p className="text-xs text-sand-800/60">{t("provisional.aou")}</p>
          <p className="text-xs text-amber-950/90">{t("map.aouNotByStac")}</p>
          <NajdSeasonalChip />
          <AlertMap />
        </section>
      ) : (
        <section className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-crop-700">{t("restoration.title")}</h2>
            <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-950">
              {t("provisional.badge")}
            </span>
            <span className="rounded-full border border-sand-300 bg-sand-100 px-2.5 py-0.5 text-xs font-medium text-sand-900">
              {t("restoration.notByFarmStac")}
            </span>
          </div>
          <p className="text-sm text-sand-800/90">{t("restoration.blurb")}</p>
          <p className="text-xs text-amber-950/90">{t("provisional.sites")}</p>
          <p className="text-xs text-sand-800/60">{t("provisional.mpi")}</p>
          <RestorationMap />
        </section>
      )}

      {mode === "agricultural" && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-sand-200 bg-white p-4 text-sm shadow-sm">
            <h2 className="mb-2 font-semibold text-crop-700">{t("map.bbox")}</h2>
            <code className="text-xs">
              [{bbox.west}, {bbox.south}, {bbox.east}, {bbox.north}]
            </code>
          </div>
          <div className="rounded-2xl border border-sand-200 bg-white p-4 text-sm shadow-sm">
            <h2 className="mb-2 font-semibold text-crop-700">{t("map.hubs")}</h2>
            <ul className="space-y-1 text-sand-800/90">
              {hubs.map((h) => (
                <li key={h.id}>
                  {i18n.language === "ar" ? h.name_ar : h.name_en}
                  <span className="text-sand-800/50">
                    {" "}
                    · {h.lat.toFixed(3)}°, {h.lon.toFixed(3)}°
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
