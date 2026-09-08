import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, Rectangle, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { useTranslation } from "react-i18next";
import hubsData from "../data/hubs.json";
import SourceCitation from "./SourceCitation";
import type { SourceInfo } from "./SourceCitation";
import AouProfilePanel from "./AouProfilePanel";
import { aouIdFromFeature, type AouFeature, type AlertKind } from "../lib/aou";
import { publicUrl } from "../lib/publicUrl";

type AlertProps = {
  alert: AlertKind;
  ndvi: number;
  ndmi: number;
  date: string;
  source: string;
  product_id: string;
  tile: string;
  cloud_cover?: number;
  pixel_count?: number;
};

type AlertFeature = AouFeature & {
  properties: AlertProps;
};

type AlertFC = {
  type: "FeatureCollection";
  features: AlertFeature[];
  properties?: {
    source?: string;
    date?: string;
    alert_counts?: Record<string, number>;
    note?: string;
    window_bbox?: number[];
  };
};

const COLORS: Record<string, string> = {
  bare: "#d6c3a3",
  healthy: "#2f6b3a",
  water_attention: "#0284c7",
  vigor_attention: "#d97706",
  unclear: "#78716c",
};

const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export default function AlertMap({
  heightClass = "h-[28rem]",
  showProfile = true,
}: {
  heightClass?: string;
  showProfile?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const [data, setData] = useState<AlertFC | null>(null);
  const [error, setError] = useState(false);
  const [hideBare, setHideBare] = useState(true);
  const [selected, setSelected] = useState<AlertFeature | null>(null);
  const { hubs, bbox } = hubsData;

  useEffect(() => {
    let cancelled = false;
    fetch(publicUrl("data/latest_alerts.geojson"))
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((j: AlertFC) => {
        if (!cancelled) setData(j);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!data) return null;
    if (!hideBare) return data;
    return {
      ...data,
      features: data.features.filter((f) => f.properties?.alert !== "bare"),
    };
  }, [data, hideBare]);

  const sourceInfo: SourceInfo | null = useMemo(() => {
    if (!data) return null;
    const sample = data.features.find((f) => f.properties?.product_id)?.properties;
    return {
      source: data.properties?.source || sample?.source,
      date: data.properties?.date || sample?.date,
      product_id: sample?.product_id,
      tile: sample?.tile,
      cloud_cover: sample?.cloud_cover,
    };
  }, [data]);

  const bounds: [[number, number], [number, number]] = [
    [bbox.south, bbox.west],
    [bbox.north, bbox.east],
  ];

  const style = (feature?: AlertFeature) => {
    const alert = feature?.properties?.alert ?? "bare";
    const isBare = alert === "bare";
    const id = feature ? aouIdFromFeature(feature) : "";
    const isSelected = selected && feature && aouIdFromFeature(selected) === id;
    return {
      color: isSelected ? "#111827" : (COLORS[alert] ?? "#999"),
      weight: isSelected ? 2 : isBare ? 0 : 0.5,
      fillColor: COLORS[alert] ?? "#999",
      fillOpacity: isBare ? 0.15 : isSelected ? 0.75 : 0.55,
    };
  };

  const onEach = (feature: AlertFeature, layer: L.Layer) => {
    const p = feature.properties;
    const kind = p.alert || "unclear";
    const label = t(`live.${kind}`, { defaultValue: kind });
    const tip = t(`live.tip_${kind}`, { defaultValue: "" });
    const tipHtml = tip ? `<div style="margin-top:6px;max-width:240px">${tip}</div>` : "";
    const aouId = aouIdFromFeature(feature);
    layer.bindPopup(
      `<strong>${aouId}</strong><br/><strong>${label}</strong>${tipHtml}<br/>NDVI ${p.ndvi} · NDMI ${p.ndmi}` +
        `<br/>${p.date} · ${p.tile}` +
        `<br/><small>${t("aou.notOfficialFarm")}</small>` +
        `<br/><small>Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer</small>` +
        `<br/><small>${p.product_id}</small>`,
    );
    layer.on({
      click: () => setSelected(feature),
    });
  };

  const mapBlock = (
    <div className={`${heightClass} w-full overflow-hidden rounded-2xl border border-sand-200 shadow-sm`}>
      <MapContainer center={bbox.center as [number, number]} zoom={9} scrollWheelZoom={false}>
        <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Rectangle bounds={bounds} pathOptions={{ color: "#2f6b3a", weight: 2, fillOpacity: 0.04 }} />
        {filtered && (
          <GeoJSON
            key={`${hideBare}-${filtered.features.length}-${i18n.language}-${selected ? aouIdFromFeature(selected) : "none"}`}
            data={filtered as never}
            style={style as never}
            onEachFeature={onEach as never}
          />
        )}
        {hubs.map((h) => (
          <Marker key={h.id} position={[h.lat, h.lon]} icon={icon}>
            <Popup>{i18n.language === "ar" ? h.name_ar : h.name_en}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm text-sand-800">
          <input type="checkbox" checked={hideBare} onChange={(e) => setHideBare(e.target.checked)} />
          {t("map.hideBare")}
        </label>
        <div className="flex flex-wrap gap-3 text-xs">
          {(["bare", "healthy", "water_attention", "vigor_attention", "unclear"] as const).map((k) => (
            <span key={k} className="inline-flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-sm" style={{ background: COLORS[k] }} />
              {t(`live.${k}`)}
            </span>
          ))}
        </div>
      </div>

      {error && <p className="text-sm text-red-700">{t("live.error")}</p>}
      {!data && !error && <p className="text-sm text-sand-800/70">{t("live.loading")}</p>}

      {showProfile ? (
        <div className="grid gap-4 lg:grid-cols-5">
          <div className="lg:col-span-3">{mapBlock}</div>
          <div className="lg:col-span-2">
            <AouProfilePanel feature={selected} onClose={() => setSelected(null)} />
          </div>
        </div>
      ) : (
        mapBlock
      )}

      <SourceCitation info={sourceInfo} />
      {data?.properties?.note && <p className="text-xs text-sand-800/60">{data.properties.note}</p>}
      <p className="text-xs text-sand-800/60">{t("aou.disclaimer")}</p>
    </div>
  );
}
