import { publicUrl } from './publicUrl';
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

/** Same-origin Vercel function: avoid browser-to-provider CORS failures. */
export async function fetchLatestSentinel2Scenes(): Promise<SceneRefresh> {
  const response = await fetch(publicUrl('api/satellite-scenes'), {
    cache: 'no-store', headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(25000),
  });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('satellite_source_unavailable');
  }
  const doc = await response.json() as SceneRefresh;
  if (!Array.isArray(doc.scenes) || !Number.isFinite(Date.parse(doc.checkedAt))) {
    throw new Error('invalid_satellite_response');
  }
  return doc;
}
