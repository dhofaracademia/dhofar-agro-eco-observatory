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

/** Expected valid-pixel count for a full 500m x 500m cell at 10m resolution. */
const EXPECTED_PIXEL_COUNT = 2500;

/**
 * Data-quality confidence 0-100, derived only from observable image-quality
 * inputs already produced by run_monitor.py: scene cloud_cover and the
 * fraction of valid (non-cloud/non-nodata) pixels actually present in this
 * cell. This is NOT an accuracy claim about the alert label itself (that
 * would require field validation, per RUN_NOTES.md) -- it only answers
 * "how much did we actually get to see this week", which is the honest
 * thing satellite optical data can tell us on its own.
 *
 * Replaces the previous confidenceStub(), which returned a number based
 * only on the alert label and NDVI and was explicitly documented as
 * "not a validated accuracy claim" -- i.e. it did not use cloud_cover or
 * pixel_count at all, even though both are already present in the schema.
 */
export function dataQualityConfidence(props: AouAlertProps): number {
  const cloud = typeof props.cloud_cover === "number" ? props.cloud_cover : 0;
  // cloud_cover in the pipeline output is a scene-level percentage (e.g. 0.87 = 0.87%).
  const cloudScore = Math.max(0, 100 - cloud * 4); // 10% scene cloud -> -40 pts

  const validFraction =
    typeof props.pixel_count === "number"
      ? Math.min(1, props.pixel_count / EXPECTED_PIXEL_COUNT)
      : 0.5; // unknown pixel_count: treat as a real gap, not a free pass
  const pixelScore = validFraction * 100;

  // Weight pixel completeness slightly higher: a clear scene that still
  // only partially covers the cell (edge of tile, nodata strip) matters
  // more for a single-cell reading than overall scene cloud percentage.
  const score = 0.4 * cloudScore + 0.6 * pixelScore;
  return Math.round(Math.max(5, Math.min(97, score)));
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
