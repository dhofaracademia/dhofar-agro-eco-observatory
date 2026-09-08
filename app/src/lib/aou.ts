export type AlertKind = "bare" | "healthy" | "water_attention" | "vigor_attention" | "unclear";

export type AouAlertProps = {
  alert: AlertKind;
  ndvi: number;
  ndmi: number;
  date: string;
  source: string;
  product_id: string;
  tile: string;
  cloud_cover?: number;
  pixel_count?: number;
  ndvi_p25_veg?: number;
  ndmi_p25_veg?: number;
};

export type AouFeature = {
  type: "Feature";
  geometry: { type: string; coordinates: number[][][] | number[][][][] };
  properties: AouAlertProps;
};

/** Centroid of outer ring (Polygon) or first polygon ring (MultiPolygon). */
export function featureCentroid(feature: AouFeature): { lon: number; lat: number } {
  const g = feature.geometry;
  let ring: number[][] | undefined;
  if (g.type === "Polygon") {
    ring = (g.coordinates as number[][][])[0];
  } else if (g.type === "MultiPolygon") {
    ring = (g.coordinates as number[][][][])[0]?.[0];
  }
  if (!ring?.length) return { lon: 0, lat: 0 };
  let sx = 0;
  let sy = 0;
  const n = ring.length - (ring.length > 1 ? 1 : 0);
  for (let i = 0; i < n; i++) {
    sx += ring[i][0];
    sy += ring[i][1];
  }
  return { lon: sx / n, lat: sy / n };
}

function hashToSixDigits(lon: number, lat: number): string {
  const s = `${lon.toFixed(5)},${lat.toFixed(5)}`;
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const n = Math.abs(h) % 1_000_000;
  return String(n).padStart(6, "0");
}

/** Stable Agricultural Observation Unit id — never an official farm name. */
export function aouIdFromFeature(feature: AouFeature): string {
  const { lon, lat } = featureCentroid(feature);
  return `AOU-NJ-${hashToSixDigits(lon, lat)}`;
}

/** Estimated area in hectares from 10 m Sentinel-2 pixels (fallback 25 ha for 500 m cell). */
export function estimatedAreaHa(props: AouAlertProps): number {
  if (typeof props.pixel_count === "number" && props.pixel_count > 0) {
    return Math.round(((props.pixel_count * 100) / 10_000) * 100) / 100;
  }
  return 25;
}

/** Stub confidence 0–100 — not a validated accuracy claim. */
export function confidenceStub(props: AouAlertProps): number {
  const base =
    props.alert === "healthy"
      ? 78
      : props.alert === "water_attention"
        ? 68
        : props.alert === "vigor_attention"
          ? 62
          : props.alert === "unclear"
            ? 45
            : 55;
  const nudge = Math.round((props.ndvi ?? 0) * 20);
  return Math.max(30, Math.min(92, base + nudge));
}

export type HealthWaterLabels = {
  healthKey: string;
  waterKey: string;
  noteKey?: string;
};

/** Map pipeline alert codes to interpretive health / water labels. */
export function mapAlertLabels(alert: AlertKind): HealthWaterLabels {
  switch (alert) {
    case "healthy":
      return { healthKey: "aou.health.stable", waterKey: "aou.water.low" };
    case "water_attention":
      return { healthKey: "aou.health.watch", waterKey: "aou.water.attention" };
    case "vigor_attention":
      return {
        healthKey: "aou.health.possibleBiotic",
        waterKey: "aou.water.moderate",
        noteKey: "aou.note.possibleBiotic",
      };
    case "bare":
      return { healthKey: "aou.health.bare", waterKey: "aou.water.na" };
    default:
      return { healthKey: "aou.health.unclear", waterKey: "aou.water.unclear" };
  }
}
