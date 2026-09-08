import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function Home() {
  const { t } = useTranslation();
  const { locale = "en" } = useParams();
  const base = `/${locale}`;

  return (
    <div className="space-y-10">
      <section className="grid gap-8 lg:grid-cols-2 lg:items-center">
        <div className="space-y-4">
          <span className="inline-block rounded-full bg-sand-100 px-3 py-1 text-xs font-semibold text-earth-600">
            {t("home.badge")}
          </span>
          <h1 className="text-3xl font-bold tracking-tight text-sand-900 sm:text-4xl">
            {t("home.title")}
          </h1>
          <p className="text-base leading-relaxed text-sand-800/90">{t("home.intro")}</p>
          <p className="text-sm text-sand-800/60">{t("home.previewNote")}</p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link to={`${base}/gallery`} className="rounded-full bg-crop-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-crop-700">
              {t("home.ctaGallery")}
            </Link>
            <Link to={`${base}/analysis`} className="rounded-full border border-sand-300 bg-white px-5 py-2.5 text-sm font-semibold text-sand-800 hover:bg-sand-100">
              {t("home.ctaAnalysis")}
            </Link>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <figure className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-sm sm:col-span-2">
            <img
              src="/previews/39QZV_20260313_truecolor_wheatseason_Thumrait.png"
              alt="Thumrait true-color"
              className="h-48 w-full object-cover sm:h-56"
            />
            <figcaption className="px-3 py-2 text-xs text-sand-800/70">Thumrait · true-color · 2026-03-13</figcaption>
          </figure>
          <figure className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-sm">
            <img
              src="/previews/39QZV_20260313_NDVI_Thumrait.png"
              alt="Thumrait NDVI"
              className="h-36 w-full object-cover"
            />
            <figcaption className="px-3 py-2 text-xs text-sand-800/70">NDVI</figcaption>
          </figure>
          <figure className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-sm">
            <img
              src="/previews/39QZV_20260904_truecolor_Thumrait.png"
              alt="Thumrait late summer"
              className="h-36 w-full object-cover"
            />
            <figcaption className="px-3 py-2 text-xs text-sand-800/70">Late summer</figcaption>
          </figure>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-crop-700">{t("home.whyTitle")}</h2>
          <p className="text-sm leading-relaxed text-sand-800/90">{t("home.whyBody")}</p>
        </div>
        <div className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-crop-700">{t("home.seasonTitle")}</h2>
          <p className="text-sm leading-relaxed text-sand-800/90">{t("home.seasonBody")}</p>
        </div>
      </section>
    </div>
  );
}
