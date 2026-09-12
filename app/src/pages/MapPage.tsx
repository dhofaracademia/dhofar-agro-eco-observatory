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
import MountainStatusPanel from "../components/MountainStatusPanel";

type Hub = (typeof hubsData.hubs)[number];

function HubCoverageBadge({ hub }: { hub: Hub }) {
  const { t } = useTranslation();
  if (!hub.within_satellite_aoi) {
    return (
      <span className="ms-1 inline-flex rounded-full border border-amber-400 bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-950">
        {t("map.hubOutsideAoi")}
      </span>
    );
  }
  if (!hub.covered_by_current_window) {
    return (
      <span className="ms-1 inline-flex rounded-full border border-sand-300 bg-sand-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sand-800">
        {t("map.hubOutsideWindow")}
      </span>
    );
  }
  return null;
}

export default function MapPage() {
  const { t, i18n } = useTranslation();
  const { hubs, bbox } = hubsData;
  const analysisWindow = "analysis_window" in hubsData ? hubsData.analysis_window : null;
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
          <MountainStatusPanel />
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
            {analysisWindow && (
              <div className="mt-3 border-t border-sand-100 pt-3">
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-sand-800/50">
                  {t("map.analysisWindow")}
                </h3>
                <code className="text-xs">
                  [{analysisWindow.west}, {analysisWindow.south}, {analysisWindow.east}, {analysisWindow.north}]
                </code>
                <p className="mt-2 text-xs text-sand-800/70">{t("map.aouBboxVsWindow")}</p>
              </div>
            )}
          </div>
          <div className="rounded-2xl border border-sand-200 bg-white p-4 text-sm shadow-sm">
            <h2 className="mb-2 font-semibold text-crop-700">{t("map.hubs")}</h2>
            <p className="mb-2 text-xs text-sand-800/70">{t("map.hubCoverageLegend")}</p>
            <ul className="space-y-2 text-sand-800/90">
              {hubs.map((h) => {
                const dimmed = !h.covered_by_current_window;
                return (
                  <li
                    key={h.id}
                    className={dimmed ? "opacity-50" : undefined}
                  >
                    <span className={dimmed ? "text-sand-800/80" : undefined}>
                      {i18n.language === "ar" ? h.name_ar : h.name_en}
                    </span>
                    <span className="text-sand-800/50">
                      {" "}
                      · {h.lat.toFixed(3)}°, {h.lon.toFixed(3)}°
                    </span>
                    <HubCoverageBadge hub={h} />
                    {h.id === "mazyunah" && (
                      <p className="mt-1 text-xs leading-relaxed text-amber-950/90">
                        {t("map.hubMazyunahNote")}
                      </p>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
