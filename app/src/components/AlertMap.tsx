import { fetchReleaseData } from "../lib/releaseData";
import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, Rectangle, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import { useTranslation } from "react-i18next";
import hubsData from "../data/hubs.json";
import SourceCitation from "./SourceCitation";
import type { SourceInfo } from "./SourceCitation";
import AouProfilePanel from "./AouProfilePanel";
import { aouIdFromFeature, type AouFeature, type AlertKind } from "../lib/aou";
import NajdSeasonalChip from "./NajdSeasonalChip";

type AlertProps = {
  alert: AlertKind;
  ndvi: number;
  ndmi: number;
  date: string;
  source?: string;
  product_id?: string;
  tile?: string;
  cloud_cover?: number;
  pixel_count?: number;
  temporal_evidence_sufficient?: boolean;
};

function displayAlert(props?: Pick<AlertProps, "alert" | "temporal_evidence_sufficient">): AlertKind {
  const raw = props?.alert ?? "unclear";
  if (props?.temporal_evidence_sufficient === false && raw !== "bare" && raw !== "unclear") {
    return "unclear";
  }
  return raw;
}

function FitAouLayer({ features, active }: { features: AlertFeature[]; active: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (!active || features.length === 0) return;
    const bounds = L.geoJSON(features as never).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [32, 32], maxZoom: 12 });
  }, [features, active, map]);
  return null;
}

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

const icon = L.divIcon({
  className: "hub-pin",
  html: '<span class="hub-pin-dot"></span>',
  iconSize: [14, 14],
  iconAnchor: [7, 7],
  popupAnchor: [0, -8],
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
  const [showDebugGrid, setShowDebugGrid] = useState(false);
  const [selected, setSelected] = useState<AlertFeature | null>(null);
  const { hubs, bbox } = hubsData;
  const analysisWindow =
    "analysis_window" in hubsData
      ? (hubsData as typeof hubsData & {
          analysis_window: { west: number; south: number; east: number; north: number };
        }).analysis_window
      : null;

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(false);
    setSelected(null);
    const path = showDebugGrid ? "data/latest_alerts.geojson" : "data/aou/aou_registry.geojson";
    fetchReleaseData(path)
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
  }, [showDebugGrid]);

  const filtered = useMemo(() => {
    if (!data) return null;
    return {
      ...data,
      features: data.features.filter((f) => {
        const kind = displayAlert(f.properties);
        return !(hideBare && kind === "bare");
      }),
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
  const windowBounds: [[number, number], [number, number]] | null = analysisWindow
    ? [
        [analysisWindow.south, analysisWindow.west],
        [analysisWindow.north, analysisWindow.east],
      ]
    : null;

  const style = (feature?: AlertFeature) => {
    const alert = displayAlert(feature?.properties);
    const isBare = alert === "bare";
    const id = feature ? aouIdFromFeature(feature) : "";
    const isSelected = selected && feature && aouIdFromFeature(selected) === id;
    return {
      color: isSelected ? "#111827" : (COLORS[alert] ?? "#999"),
      weight: isSelected ? 2 : isBare ? 0 : showDebugGrid ? 0.5 : 2,
      fillColor: COLORS[alert] ?? "#999",
      fillOpacity: isBare ? 0.15 : isSelected ? 0.75 : 0.55,
    };
  };

  const onEach = (feature: AlertFeature, layer: L.Layer) => {
    const p = feature.properties;
    const kind = displayAlert(p);
    const downgraded = kind === "unclear" && p.alert && p.alert !== "unclear" && p.alert !== "bare";
    const label = t(`live.${kind}`, { defaultValue: kind });
    const tip = t(`live.tip_${kind}`, { defaultValue: "" });
    const tipHtml = tip ? `<div style="margin-top:6px;max-width:240px">${tip}</div>` : "";
    const downgradedHtml = downgraded
      ? `<div style="margin-top:6px;max-width:240px">${t("map.downgradedUnclear", {
          defaultValue: i18n.language?.startsWith("ar")
            ? "المشاهدات لا تكفي لإظهار تنبيه الانتباه هذا."
            : "Not enough observations to show this attention flag.",
        })}</div>`
      : "";
    const aouId = aouIdFromFeature(feature);
    const when = [p.date, p.tile].filter(Boolean).join(" · ");
    layer.bindPopup(
      `<strong>\( {aouId}</strong><br/><strong> \){label}</strong>\( {tipHtml} \){downgradedHtml}<br/>NDVI ${p.ndvi ?? "—"} · NDMI ${p.ndmi ?? "—"}` +
        (when ? `<br/>${when}` : "") +
        `<br/><small>${t("aou.notOfficialFarm")}</small>` +
        `<br/><small>Copernicus Sentinel-2 L2A (ESA) via Microsoft Planetary Computer</small>` +
        (p.product_id ? `<br/><small>${p.product_id}</small>` : ""),
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
        {windowBounds && (
          <Rectangle
            bounds={windowBounds}
            pathOptions={{ color: "#b45309", weight: 2, dashArray: "6 4", fillOpacity: 0.06 }}
          />
        )}
        {filtered && (
          <GeoJSON
            key={`\( {showDebugGrid}- \){hideBare}-\( {filtered.features.length}- \){i18n.language}-${selected ? aouIdFromFeature(selected) : "none"}`}
            data={filtered as never}
            style={style as never}
            onEachFeature={onEach as never}
          />
        )}
        {filtered && <FitAouLayer features={filtered.features} active={!showDebugGrid} />}
        {hubs.map((h) => {
          const inWindow = Boolean(h.covered_by_current_window);
          const inAoi = Boolean(h.within_satellite_aoi);
          const name = i18n.language === "ar" ? h.name_ar : h.name_en;
          const badge = !inAoi
            ? t("map.hubOutsideAoi")
            : !inWindow
              ? t("map.hubOutsideWindow")
              : null;
          return (
            <Marker key={h.id} position={[h.lat, h.lon]} icon={icon} opacity={inWindow ? 1 : 0.4}>
              <Popup>
                <div>
                  <strong>{name}</strong>
                  {badge && (
                    <div style={{ marginTop: 6, fontSize: 12, opacity: 0.9 }}>{badge}</div>
                  )}
                  {h.id === "mazyunah" && (
                    <div style={{ marginTop: 6, fontSize: 12, maxWidth: 240 }}>
                      {t("map.hubMazyunahNote")}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
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
        <label className="flex items-center gap-2 text-sm text-sand-800">
          <input type="checkbox" checked={showDebugGrid} onChange={(e) => setShowDebugGrid(e.target.checked)} />
          {t("map.showDebugGrid", {
            defaultValue: i18n.language?.startsWith("ar")
              ? "أظهر شبكة التصحيح 500 م"
              : "Show 500 m debug grid",
          })}
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
      {showDebugGrid && (
        <p className="text-xs leading-relaxed text-amber-950">
          {t("map.debugGridNote", {
            defaultValue: i18n.language?.startsWith("ar")
              ? "طبقة تصحيح فقط، والملف كبير. الخلايا التي لا تملك مشاهدات كافية تُعرض كدليل غير كافٍ، لا كحالة سليمة أو إجهاد رطوبة."
              : "Debug layer only, and a large download. Cells without enough observations are shown as unclear, not as healthy or moisture stress.",
          })}
        </p>
      )}
      <NajdSeasonalChip always />

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

      <p className="text-xs text-sand-800/70">{t("map.hubCoverageLegend")}</p>
      <SourceCitation info={sourceInfo} />
      {data?.properties?.note && <p className="text-xs text-sand-800/60">{data.properties.note}</p>}
      <p className="text-xs text-sand-800/60">{t("aou.disclaimer")}</p>
    </div>
  );
}
