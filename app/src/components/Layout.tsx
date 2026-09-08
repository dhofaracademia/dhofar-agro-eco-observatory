import { Link, NavLink, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3 py-1.5 text-sm font-medium transition ${
    isActive ? "bg-crop-600 text-white" : "text-sand-800 hover:bg-sand-100"
  }`;

export default function Layout({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  const { locale = "en" } = useParams();
  const other = locale === "ar" ? "en" : "ar";
  const base = `/${locale}`;
  const title =
    i18n.language === "ar"
      ? t("appName")
      : t("appName");
  const subtitleSecondary =
    i18n.language === "ar" ? "Dhofar Agro & Eco Observatory" : "مرصد ظفار الزراعي البيئي";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-20 border-b border-sand-200/80 bg-sand-50/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to={base} className="min-w-0">
            <div className="text-lg font-bold text-crop-700">{title}</div>
            <div className="text-xs font-medium text-crop-700/80">{t("appAlias")}</div>
            <div className="truncate text-xs text-sand-800/70">
              {t("subtitle")}
              <span className="text-sand-800/40"> · {subtitleSecondary}</span>
            </div>
          </Link>
          <nav className="flex flex-wrap items-center gap-1">
            <NavLink to={base} end className={linkClass}>
              {t("nav.home")}
            </NavLink>
            <NavLink to={`${base}/gallery`} className={linkClass}>
              {t("nav.gallery")}
            </NavLink>
            <NavLink to={`${base}/map`} className={linkClass}>
              {t("nav.map")}
            </NavLink>
            <NavLink to={`${base}/analysis`} className={linkClass}>
              {t("nav.analysis")}
            </NavLink>
            <NavLink to={`${base}/about`} className={linkClass}>
              {t("nav.about")}
            </NavLink>
            <Link
              to={`/${other}`}
              className="ms-2 rounded-full border border-sand-300 px-3 py-1.5 text-sm font-semibold text-sand-800 hover:bg-sand-100"
            >
              {other === "ar" ? "ع" : "EN"}
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
      <footer className="border-t border-sand-200 py-5 text-center text-xs text-sand-800/60">
        <div>{t("footer")}</div>
        <div className="mx-auto mt-2 max-w-3xl px-4">{t("gallery.howRefresh")}</div>
        <div className="mt-2 font-medium text-sand-800/70">{t("about.dataSourcesTitle")}</div>
      </footer>
    </div>
  );
}
