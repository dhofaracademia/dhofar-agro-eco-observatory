import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { useTranslation } from "react-i18next";
import { publicUrl } from "../lib/publicUrl";

type Boundary = Feature<Geometry, { id: string; name_ar: string; name_en: string }>;
type Cell = Feature<Geometry, { id: string; ndvi: number | null; ndmi: number | null; ndvi_change: number | null; date: string; previous_date: string | null; clear_fraction: number }>;
type Observation = { region_id: string; date: string; previous_date: string | null; area_km2: number; estimated_clear_area_km2: number; clear_fraction: number; cells: Cell[]; sources: { id: string; datetime: string }[] };
type Observations = { generated_at: string; boundary_sha256: string; regions: Observation[] };

function FitRegion({ feature }: { feature: Boundary }) {
  const map = useMap();
  useEffect(() => { map.fitBounds(L.geoJSON(feature).getBounds(), { padding: [20, 20], animate: false }); }, [feature, map]);
  return null;
}
function color(value: number | null | undefined, change: boolean) {
  if (value == null || !Number.isFinite(value)) return "#78716c";
  if (change) return value > 0.05 ? "#166534" : value < -0.05 ? "#b45309" : "#e7dfcb";
  return value > 0.5 ? "#166534" : value > 0.3 ? "#65a30d" : value > 0.18 ? "#d9c85b" : "#d6c3a3";
}

export default function RegionalMap() {
  const { i18n } = useTranslation();
  const ar = i18n.language.startsWith("ar");
  const txt = (a: string, e: string) => ar ? a : e;
  const [boundaries, setBoundaries] = useState<FeatureCollection<Geometry, Boundary["properties"]> | null>(null);
  const [observations, setObservations] = useState<Observations | null>(null);
  const [selected, setSelected] = useState("salalah-plain");
  const [change, setChange] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [failed, setFailed] = useState(false);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true); setError(false); setFailed(false); setObservations(null);
      try {
        const options = { signal: controller.signal, cache: "no-cache" as RequestCache };
        const br = await fetch(publicUrl("data/regions/boundaries.geojson"), options);
        if (!br.ok) throw new Error("Boundaries unavailable");
        const raw = await br.text();
        const b = JSON.parse(raw);
        if (b.type !== "FeatureCollection" || !b.features?.length) throw new Error("Invalid boundaries");
        setBoundaries(b);
        const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw));
        const hash = Array.from(new Uint8Array(digest)).map(n => n.toString(16).padStart(2,"0")).join("");
        const response = await fetch(publicUrl("data/regions/observations.json"), options);
        if (response.status === 404) { setObservations(null); }
        else {
          if (!response.ok) throw new Error("Observations unavailable");
          const data = await response.json();
          if (data.schema_version !== 1 || !Array.isArray(data.regions) || data.boundary_sha256 !== hash) throw new Error("Observation/boundary version mismatch");
          setObservations(data);
        }
        const status = await fetch(publicUrl("data/regions/status.json"), options);
        if (status.ok) setFailed((await status.json()).status === "failed");
      } catch (e) {
        if (!controller.signal.aborted) { setError(true); setObservations(null); }
      } finally { if (!controller.signal.aborted) setLoading(false); }
    }
    void load();
    return () => controller.abort();
  }, [revision]);
  const feature = boundaries?.features.find(f => f.properties.id === selected);
  const reading = observations?.regions.find(r => r.region_id === selected);
  const stale = reading ? Date.now() - Date.parse(reading.date) > 14*86400000 : false;
  const number = (n: number) => n.toLocaleString(ar ? "ar-OM" : "en", { maximumFractionDigits: 1 });
  return <section className="space-y-4 rounded-2xl border border-sand-200 bg-white p-4" aria-label={txt("الرصد الإقليمي", "Regional monitoring")}>
    <h2 className="text-xl font-bold text-crop-700">{txt("استكشف مساحات أوسع من ظفار", "Explore wider areas of Dhofar")}</h2>
    <p className="text-sm leading-relaxed">{txt("اختر نطاقًا لمشاهدة اختلاف الاخضرار داخله. هذه حدود دراسة رسمناها للرصد، وليست حدودًا رسمية أو تغطية كاملة للمنطقة المسماة.", "Choose a study area to explore vegetation differences. These are observatory-defined study footprints, not official boundaries or complete coverage of the named region.")}</p>
    <div className="flex flex-wrap gap-3">
      <label className="flex flex-col gap-1 text-sm font-semibold">{txt("منطقة الرصد", "Study area")}
        <select value={selected} onChange={e => setSelected(e.target.value)} className="rounded-lg border border-sand-300 bg-white p-2">
          {boundaries?.features.map(f => <option key={f.properties.id} value={f.properties.id}>{ar ? f.properties.name_ar : f.properties.name_en}</option>)}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm font-semibold">{txt("ماذا تريد أن ترى؟", "What would you like to see?")}
        <select value={change ? "change" : "greenness"} onChange={e => setChange(e.target.value === "change")} className="rounded-lg border border-sand-300 bg-white p-2">
          <option value="greenness">{txt("الاخضرار في آخر صورة", "Greenness in the latest image")}</option>
          <option value="change">{txt("التغيّر بين صورتين", "Change between two images")}</option>
        </select>
      </label>
      <button disabled={loading} onClick={() => setRevision(v => v+1)} className="self-end rounded-lg bg-crop-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{txt("تحقق من التحديثات", "Check for updates")}</button>
    </div>
    <p className="text-xs text-sand-800">{txt("تُفحص الصور يوميًا؛ الزر يجلب النتائج المنشورة ولا يطلب تصويرًا جديدًا. قد تحجب السحب أو الظلال بعض الأجزاء.", "Images are checked daily; this button retrieves published results, not a new satellite acquisition. Clouds or shadows may obscure parts of an area.")}</p>
    <div aria-live="polite">
      {loading && <p>{txt("جارٍ تحميل التغطية…", "Loading coverage…")}</p>}
      {error && <p role="alert">{txt("تعذّر تحميل قراءات متوافقة مع الحدود. حاول مجددًا.", "Could not load readings matching these boundaries. Please retry.")}</p>}
      {!loading && !error && !reading && <p>{txt("النطاق مضاف. لم تُنشر أول قراءة له بعد؛ الحدود المعروضة لا تعني توافر قياسات.", "Study area added. Its first reading has not been published; displayed boundaries do not imply measurements are available.")}</p>}
      {failed && <p className="text-amber-900">{txt("تعذّر آخر تحديث آلي. نعرض آخر نتيجة منشورة إن توفرت.", "The last automatic update failed. The last published result is shown when available.")}</p>}
      {stale && <p className="text-amber-900">{txt("الصورة أقدم من أسبوعين؛ لا تمثل الحالة الحالية بالضرورة.", "This image is over two weeks old and may not represent current conditions.")}</p>}
    </div>
    {reading && <div className="grid gap-3 text-sm sm:grid-cols-3">
      <p>{txt("مساحة نطاق الدراسة", "Study area size")}<strong className="block">{number(reading.area_km2)} {txt("كم²", "km²")}</strong></p>
      <p>{txt("مساحة أرض واضحة تقديريًا", "Estimated clear land area")}<strong className="block">{number(reading.estimated_clear_area_km2)} {txt("كم²", "km²")} · {number(reading.clear_fraction*100)}%</strong></p>
      <p>{txt("تاريخ التقاط الصورة", "Image acquisition date")}<strong className="block" dir="ltr">{reading.date}</strong>{change && <span dir="ltr">{reading.previous_date ?? txt("لا توجد مقارنة", "No comparison")}</span>}</p>
    </div>}
    <div className="h-[30rem] overflow-hidden rounded-xl border border-sand-200">
      <MapContainer center={[17.5,54]} zoom={8} scrollWheelZoom={false}>
        <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {feature && <FitRegion feature={feature} />}
        {feature && <GeoJSON key={`boundary-${selected}`} data={feature} style={{color:"#245530",weight:3,fillOpacity:0.03}} />}
        {reading && <GeoJSON key={`${selected}-${observations?.generated_at}-${change}-${ar}`} data={{type:"FeatureCollection", features:reading.cells} as FeatureCollection} style={f => ({weight:0.3,color:"#fff",fillOpacity:0.7,fillColor:color(change ? f?.properties.ndvi_change : f?.properties.ndvi, change)})} onEachFeature={(f, layer) => {
          const p = f.properties;
          const content = document.createElement("div");
          content.dir = ar ? "rtl" : "ltr";
          const value = change ? p.ndvi_change : p.ndvi;
          content.textContent = `${txt("تاريخ الصورة", "Image date")}: ${p.date}. ${txt("تغطية واضحة", "Clear coverage")}: ${number(p.clear_fraction*100)}%. ${value == null ? txt("مشاهدات غير كافية لهذه الخلية", "Insufficient observations for this cell") : change ? txt("تغيّر الاخضرار", "Greenness change")+`: ${value}` : txt("مؤشر الاخضرار", "Greenness index")+`: ${value}`}`;
          layer.bindPopup(content);
        }} />}
      </MapContainer>
    </div>
    <p className="text-sm">{change ? txt("أخضر: زيادة الاخضرار • بني: انخفاضه • بيج: تغيّر محدود • رمادي: لا تكفي بيانات المقارنة.", "Green: increasing greenness • Brown: decreasing • Beige: limited change • Grey: insufficient comparable data.") : txt("أخضر داكن: اخضرار أعلى • أصفر: اخضرار أقل • بيج: اخضرار منخفض جدًا • رمادي: بيانات غير كافية.", "Dark green: higher greenness • Yellow: lower • Beige: very low • Grey: insufficient data.")}</p>
    <p className="text-sm">{txt("كل خلية تلخص جزءًا من المنطقة، وليست حدود مزرعة. انخفاض الاخضرار قد يكون موسميًا؛ لا يثبت الجفاف أو تلف المحاصيل.", "Each cell summarizes part of the area, not a farm boundary. Lower greenness can be seasonal; it does not establish drought or crop damage.")}</p>
    <details className="text-sm"><summary className="cursor-pointer font-semibold">{txt("كيف حُسبت هذه القراءة؟", "How was this reading calculated?")}</summary>
      <p className="mt-2">{txt("صور Sentinel-2 مع استبعاد السحب والظلال والمياه. نأخذ عينة كل 60 مترًا، ونجمعها في خلايا بطول نحو 960 مترًا مقصوصة بحدود الدراسة. المساحة الواضحة تقدير من العينات، وليست مسحًا لكل بكسل أصلي. المقارنة تستخدم المواقع الواضحة المشتركة بين التاريخين، وتتطلب 50 عينة و50% تغطية على الأقل لكل خلية. ألوان التغيّر تستخدم حدًا وصفيًا ±0.05، وليست دلالة إحصائية أو إنذارًا زراعيًا.", "Sentinel-2 imagery excluding clouds, shadows and water. Samples every 60 m are grouped into approximately 960 m cells clipped to the study boundary. Clear area is estimated from samples, not every native pixel. Changes use the same clear locations on both dates, requiring at least 50 samples and 50% coverage per cell. Change colors use a descriptive ±0.05 threshold, not statistical significance or an agricultural alert.")}</p>
      {reading && <ul className="mt-2 break-all text-xs">{reading.sources.map(s => <li key={s.id}>{s.id}</li>)}</ul>}
      <p className="mt-2">Contains modified Copernicus Sentinel data. Source: Microsoft Planetary Computer.</p>
    </details>
  </section>;
}
