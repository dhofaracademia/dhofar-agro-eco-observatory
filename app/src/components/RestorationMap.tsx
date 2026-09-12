import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { useTranslation } from "react-i18next";
import { publicUrl } from "../lib/publicUrl";
import WhyThisSiteCard, { type RestorationSiteProps } from "./WhyThisSiteCard";

type SiteFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: RestorationSiteProps;
};

type SiteFC = {
  type: "FeatureCollection";
  features: SiteFeature[];
  properties?: { note?: string };
};

const STATUS_COLOR = "#78716c";

function FitSites({ features }: { features: SiteFeature[] }) {
  const map = useMap();
  useEffect(() => {
    if (!features.length) return;
    const latLngs = features.map((f) => [f.geometry.coordinates[1], f.geometry.coordinates[0]] as [number, number]);
    map.fitBounds(latLngs, { padding: [40, 40], maxZoom: 10 });
  }, [features, map]);
  return null;
}

export default function RestorationMap({ heightClass = "h-[28rem]" }: { heightClass?: string }) {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<SiteFC | null>(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<RestorationSiteProps | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(publicUrl("data/mountain/recommended_sites.geojson"))
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((j: SiteFC) => {
        if (!cancelled) setData(j);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const features = useMemo(() => data?.features ?? [], [data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-sand-800/80">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full" style={{ background: STATUS_COLOR }} />
          {t("mountainStatus.siteStatus")}
        </span>
        <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-950">
          {t("mountainStatus.seedingHold")}
        </span>
      </div>

      {error && <p className="text-sm text-red-700">{t("restoration.error")}</p>}
      {!data && !error && <p className="text-sm text-sand-800/70">{t("restoration.loading")}</p>}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className={`lg:col-span-3 ${heightClass} w-full overflow-hidden rounded-2xl border border-sand-200 shadow-sm`}>
          <MapContainer center={[17.05, 54.2]} zoom={9} scrollWheelZoom={false}>
            <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {features.length > 0 && <FitSites features={features} />}
            {features.map((f) => {
              const [lon, lat] = f.geometry.coordinates;
              const p = f.properties;
              const color = STATUS_COLOR;
              const name = i18n.language === "ar" ? p.name_ar ?? p.name_en : p.name_en ?? p.name_ar;
              return (
                <CircleMarker
                  key={p.id}
                  center={[lat, lon]}
                  radius={selected?.id === p.id ? 12 : 9}
                  pathOptions={{
                    color,
                    fillColor: color,
                    fillOpacity: 0.75,
                    weight: selected?.id === p.id ? 3 : 1.5,
                  }}
                  eventHandlers={{
                    click: () => setSelected(p),
                  }}
                >
                  <Popup>
                    <div style={{ maxWidth: 220 }}>
                      <strong>{p.id}</strong>
                      {name ? <div>{name}</div> : null}
                      <div style={{ fontSize: 11, marginTop: 4 }}>{t("mountainStatus.productKind")}</div>
                      <div style={{ fontSize: 11 }}>{t("mountainStatus.timingDeferred")}</div>
                      <div style={{ fontSize: 11 }}>{t("mountainStatus.noPlantHere")}</div>
                      <div style={{ fontSize: 11 }}>{t("mountainStatus.seedingHold")}</div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
        <div className="lg:col-span-2">
          <WhyThisSiteCard site={selected} onClose={() => setSelected(null)} />
        </div>
      </div>

      {data?.properties?.note && <p className="text-xs text-sand-800/60">{data.properties.note}</p>}
    </div>
  );
}
