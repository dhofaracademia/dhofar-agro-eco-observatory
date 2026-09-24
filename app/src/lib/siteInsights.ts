export type Geometry = { type: string; coordinates: number[][][] | number[][][][] };
export type Observation = {
  date?: string; ndvi?: number | null; ndmi?: number | null;
  series_scope?: string; tile?: string; assessability?: string;
  observation_role?: string; valid_area_fraction?: number | null;
  clear_fraction?: number | null;
};

/** WGS84 input, including Arabic digits. Never guess reversed coordinates. */
export function parseCoordinates(value: string): [number, number] | null {
  const text = value.trim().replace(/[٠-٩]/g, d => String(d.charCodeAt(0) - 1632))
    .replace(/[۰-۹]/g, d => String(d.charCodeAt(0) - 1776)).replace(/٫/g, '.');
  const parts = text.split(/[,،;\s]+/);
  if (parts.length !== 2 || parts.some(p => !/^[+-]?\d+(\.\d+)?$/.test(p))) return null;
  const [lat, lon] = parts.map(Number);
  return Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? [lat, lon] : null;
}

function inRing(lon: number, lat: number, ring: number[][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x, y] = ring[i], [xj, yj] = ring[j];
    const cross = (lon - x) * (yj - y) - (lat - y) * (xj - x);
    if (Math.abs(cross) < 1e-12 && lon >= Math.min(x, xj) && lon <= Math.max(x, xj) && lat >= Math.min(y, yj) && lat <= Math.max(y, yj)) return true;
    if ((y > lat) !== (yj > lat) && lon < (xj - x) * (lat - y) / (yj - y) + x) inside = !inside;
  }
  return inside;
}

/** Exact polygon containment, including holes. Nearby units are not coverage. */
export function containsPoint(geometry: Geometry, lat: number, lon: number): boolean {
  const polys = geometry.type === 'Polygon' ? [geometry.coordinates as number[][][]]
    : geometry.type === 'MultiPolygon' ? geometry.coordinates as number[][][][] : [];
  return polys.some(rings => rings.length > 0 && inRing(lon, lat, rings[0]) && !rings.slice(1).some(r => inRing(lon, lat, r)));
}

export function comparison(observations: Observation[]) {
  const dated = observations.filter(o => o.date && /^\d{4}-\d{2}-\d{2}$/.test(o.date))
    .sort((a, b) => b.date!.localeCompare(a.date!));
  const latest = dated[0];
  const valid = (o: Observation) => o.assessability === 'assessable' && o.observation_role !== 'retained_last_good'
    && Number.isFinite(o.ndvi) && Number.isFinite(o.ndmi)
    && (o.valid_area_fraction ?? o.clear_fraction ?? 0) >= 0.2;
  if (!latest || !valid(latest)) return { reason: 'quality' as const };
  if (!latest.series_scope || latest.series_scope === 'window_not_aou') return { reason: 'method' as const };
  const older = dated.filter(o => o.date! < latest.date! && valid(o));
  if (!older.length) return { reason: 'history' as const };
  const previous = older.find(o => o.series_scope === latest.series_scope && o.tile === latest.tile);
  if (!previous) return { reason: 'method' as const };
  return { reason: null, latest, previous, ndvi: latest.ndvi! - previous.ndvi!, ndmi: latest.ndmi! - previous.ndmi! };
}
