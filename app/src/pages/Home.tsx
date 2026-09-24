import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { publicUrl } from "../lib/publicUrl";
import ReadingStatus from "../components/ReadingStatus";
import KhareefCalendar from "../components/KhareefCalendar";

export default function Home() {
  const { t, i18n } = useTranslation();
  const { locale = "en" } = useParams();
  const base = `/${locale}`;
  const archiveNote = i18n.language?.startsWith("ar")
    ? "صورة أرشيفية، وليست القراءة الحية."
    : "Archive image, not the live reading.";

  return (
    <div className="space-y-10">
      <section className="rounded-2xl bg-crop-700 p-5 text-white sm:p-8">
        <p className="text-sm">{t("simple.noExpertise")}</p>
        <h1 className="mt-2 text-2xl font-bold sm:text-3xl">{t("simple.startTitle")}</h1>
        <p className="mt-2 max-w-2xl leading-relaxed">{t("simple.startIntro")}</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link to={`${base}/map`} className="rounded-full bg-white px-5 py-3 font-semibold text-crop-700">{t("simple.startMap")}</Link>
          <Link to={`${base}/analysis`} className="rounded-full border border-white px-5 py-3 font-semibold">{t("explore.start")}</Link>
          <Link to={`${base}/guide`} className="rounded-full border border-white px-5 py-3 font-semibold">{t("simple.learn")}</Link>
        </div>
      </section>
      <ReadingStatus />
      <section className="space-y-3">
        <p className="text-sm text-sand-800/70">{t("home.previewNote")}</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <figure className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-sm sm:col-span-2">
            <img
              src={publicUrl("previews/39QZV_20260313_truecolor_wheatseason_Thumrait.png")}
              alt="Thumrait true-color"
              className="h-48 w-full object-cover sm:h-56"
            />
            <figcaption className="px-3 py-2 text-xs text-sand-800/70">
              Thumrait · true-color · 2026-03-13 · {archiveNote}
            </figcaption>
          </figure>
          <figure className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-sm">
            <img
              src={publicUrl("previews/39QZV_20260313_NDVI_Thumrait.png")}
              alt="Thumrait NDVI"
              className="h-36 w-full object-cover"
            />
            <figcaption className="px-3 py-2 text-xs text-sand-800/70">NDVI · 2026-03-13 · {archiveNote}</figcaption>
          </figure>
          <figure className="overflow-hidden rounded-2xl border border-sand-200 bg-white shadow-sm">
            <img
              src={publicUrl("previews/39QZV_20260904_truecolor_Thumrait.png")}
              alt="Thumrait late summer"
              className="h-36 w-full object-cover"
            />
            <figcaption className="px-3 py-2 text-xs text-sand-800/70">
              Thumrait · 2026-09-04 · {archiveNote}
            </figcaption>
          </figure>
        </div>
      </section>

      <KhareefCalendar />

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-crop-700">{t("home.agroTitle")}</h2>
          <p className="text-sm leading-relaxed text-sand-800/90">{t("home.agroBody")}</p>
        </div>
        <div className="rounded-2xl border border-sand-200 bg-white p-5 shadow-sm">
          <h2 className="mb-2 text-lg font-semibold text-crop-700">{t("home.restoTitle")}</h2>
          <p className="text-sm leading-relaxed text-sand-800/90">{t("home.restoBody")}</p>
        </div>
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
