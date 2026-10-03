import { publicUrl } from './publicUrl';
import trustedHosts from '../data/trustedSatelliteHosts.json';
export type StacScene = {
  id: string;
  datetime: string | null;
  date: string | null;
  cloudCover: number | null;
  tile: string | null;
  collection: string;
  previewUrl: string | null;
  selfHref: string | null;
};
export type RefreshStatus = 'idle' | 'refreshing' | 'updated' | 'failed';
export const OBSERVATORY_BBOX = [53.4, 17.5, 54.3, 18.5] as const;
export type SceneRefresh = { scenes: StacScene[]; checkedAt: string; newestCapture: string | null };

export function trustedSatelliteUrl(value: unknown, hosts = trustedHosts.preview): string | null {
  if (typeof value !== 'string' || value.length > 4096) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password && !url.port
      && hosts.includes(url.hostname) ? url.href : null;
  } catch { return null; }
}

/** Treat both catalogue responses and saved browser data as untrusted input. */
export function sanitizeScenes(value: unknown): StacScene[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  const result: StacScene[] = [];
  for (const item of value.slice(0, 100)) {
    if (!item || typeof item.id !== 'string' || !item.id || item.id.length > 256 || seen.has(item.id)
      || typeof item.datetime !== 'string' || !Number.isFinite(Date.parse(item.datetime))) continue;
    seen.add(item.id);
    const datetime = new Date(item.datetime).toISOString();
    result.push({ id: item.id, datetime, date: datetime.slice(0, 10), collection: 'sentinel-2-l2a',
      cloudCover: Number.isFinite(item.cloudCover) && item.cloudCover >= 0 && item.cloudCover <= 100 ? item.cloudCover : null,
      tile: typeof item.tile === 'string' && /^[0-9A-Z]{5,6}$/.test(item.tile) ? item.tile : null,
      previewUrl: trustedSatelliteUrl(item.previewUrl),
      selfHref: trustedSatelliteUrl(item.selfHref, trustedHosts.catalogue),
    });
    if (result.length === 6) break;
  }
  return result;
}

/** Same-origin Vercel function: avoid browser-to-provider CORS failures. */
export async function fetchLatestSentinel2Scenes(): Promise<SceneRefresh> {
  const response = await fetch(publicUrl('api/satellite-scenes'), {
    cache: 'no-store', headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(25000),
  });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('satellite_source_unavailable');
  }
  const doc = await response.json() as SceneRefresh;
  if (!doc || !Array.isArray(doc.scenes) || !Number.isFinite(Date.parse(doc.checkedAt))) {
    throw new Error('invalid_satellite_response');
  }
  const scenes = sanitizeScenes(doc.scenes);
  return { scenes, checkedAt: doc.checkedAt, newestCapture: scenes[0]?.datetime ?? null };
}
