import { Link, NavLink, useParams, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import BrandLogo from "./BrandLogo";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3 py-1.5 text-sm font-medium transition ${
    isActive ? "bg-crop-600 text-white" : "text-sand-800 hover:bg-sand-100"
  }`;

export default function Layout({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { locale = "en" } = useParams();
  const location = useLocation();
  const other = locale === "ar" ? "en" : "ar";
  const base = `/${locale}`;

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:block focus:bg-white focus:p-4">{t("simple.skip")}</a>
      <header className="sticky top-0 z-20 border-b border-sand-200/80 bg-sand-50/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to={base} className="flex min-w-0 max-w-full items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-crop-700">
            <BrandLogo />
            <div className="min-w-0">
              <div className="text-base font-bold text-crop-700 sm:text-lg">{t("appName")}</div>
            <div className="mt-1 text-xs text-sand-800/70">
              {t("subtitle")}
            </div>
            </div>
          </Link>
          <nav aria-label={t("simple.navigation")} className="flex flex-wrap items-center gap-1">
            <NavLink to={base} end className={linkClass}>
              {t("nav.home")}
            </NavLink>
            <NavLink to={`${base}/guide`} className={linkClass}>{t("simple.guide")}</NavLink>
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
              to={{ pathname: location.pathname.replace(/^\/(ar|en)(?=\/|$)/, `/${other}`), search: location.search, hash: location.hash }}
              className="ms-2 rounded-full border border-sand-300 px-3 py-1.5 text-sm font-semibold text-sand-800 hover:bg-sand-100"
            >
              {other === "ar" ? "العربية" : "English"}
            </Link>
          </nav>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
      <footer className="border-t border-sand-200 py-5 text-center text-xs text-sand-800/60">
        <Link to={base} className="mb-3 inline-flex rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-crop-700"><BrandLogo footer /></Link>
        <div>
          {t("appName")}
        </div>
        <div className="mt-1">{t("footer")}</div>
        <div className="mx-auto mt-2 max-w-3xl px-4">{t("gallery.howRefresh")}</div>
        <div className="mt-2 font-medium text-sand-800/70">{t("about.dataSourcesTitle")}</div>
      </footer>
    </div>
  );
}
