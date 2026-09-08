import { useTranslation } from "react-i18next";
import AlertMap from "../components/AlertMap";
import hubsData from "../data/hubs.json";

export default function MapPage() {
  const { t, i18n } = useTranslation();
  const { hubs, bbox } = hubsData;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-sand-900">{t("map.title")}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-sand-800/90">{t("map.blurb")}</p>
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-crop-700">{t("map.liveTitle")}</h2>
        <p className="text-sm text-sand-800/90">{t("map.liveBlurb")}</p>
        <AlertMap />
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-sand-200 bg-white p-4 text-sm shadow-sm">
          <h2 className="mb-2 font-semibold text-crop-700">{t("map.bbox")}</h2>
          <code className="text-xs">[{bbox.west}, {bbox.south}, {bbox.east}, {bbox.north}]</code>
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
    </div>
  );
}
