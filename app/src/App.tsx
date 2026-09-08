import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import MapPage from "./pages/MapPage";
import Gallery from "./pages/Gallery";
import Analysis from "./pages/Analysis";
import About from "./pages/About";

function LocaleRoutes() {
  const { locale } = useParams();
  const { i18n } = useTranslation();

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
      <Routes>
        <Route index element={<Home />} />
        <Route path="map" element={<MapPage />} />
        <Route path="gallery" element={<Gallery />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="about" element={<About />} />
        <Route path="*" element={<Navigate to={`/${locale}`} replace />} />
      </Routes>
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
