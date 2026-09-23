import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { lazy, Suspense, useEffect } from "react";
import { useTranslation } from "react-i18next";
import Layout from "./components/Layout";
import Home from "./pages/Home";
const MapPage = lazy(() => import("./pages/MapPage"));
const Gallery = lazy(() => import("./pages/Gallery"));
const Analysis = lazy(() => import("./pages/Analysis"));
const About = lazy(() => import("./pages/About"));

const Guide = lazy(() => import("./pages/Guide"));

function LocaleRoutes() {
  const { locale } = useParams();
  const { i18n, t } = useTranslation();

  useEffect(() => {
    const lng = locale === "ar" ? "ar" : "en";
    if (i18n.language !== lng) void i18n.changeLanguage(lng);
    document.documentElement.lang = lng;
    document.documentElement.dir = lng === "ar" ? "rtl" : "ltr";
  }, [locale, i18n]);

  if (locale !== "en" && locale !== "ar") {
    return <Navigate to="/en" replace />;
  }

  return (
    <Layout>
      <Suspense fallback={<p role="status" className="py-12 text-center">{t("simple.loading")}</p>}>
      <Routes>
        <Route index element={<Home />} />
        <Route path="map" element={<MapPage />} />
        <Route path="gallery" element={<Gallery />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="guide" element={<Guide />} />
        <Route path="about" element={<About />} />
        <Route path="*" element={<Navigate to={`/${locale}`} replace />} />
      </Routes>
      </Suspense>
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/en" replace />} />
      <Route path="/:locale/*" element={<LocaleRoutes />} />
    </Routes>
  );
}
