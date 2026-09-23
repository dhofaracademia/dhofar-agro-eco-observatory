import { publicUrl } from './publicUrl';

type Release = { release_id: string; path: string };
let release: Promise<Release | null> | undefined;

/** Pin one immutable release for this page session; never mix per-file fallbacks. */
export function getRelease(): Promise<Release | null> {
  if (!release) {
    release = fetch(publicUrl('data/latest_release.json'), { cache: 'no-store' }).then(async (r) => {
      // Older deployments have no manifest and may serve their SPA HTML for missing files.
      if (r.status === 404 || r.ok && r.headers.get('content-type')?.includes('text/html')) return null;
      if (!r.ok) throw new Error('Release manifest unavailable');
      const doc = await r.json() as Release;
      if (!/^[A-Za-z0-9_-]+$/.test(doc.release_id) || doc.path !== `releases/${doc.release_id}`) {
        throw new Error('Invalid release manifest');
      }
      return doc;
    }).catch((error: unknown) => {
      release = undefined; // A transient fetch error must remain retryable.
      throw error;
    });
  }
  return release;
}

export async function fetchReleaseData(path: string): Promise<Response> {
  if (!path.startsWith('data/') || path.includes('..')) throw new Error('Invalid data path');
  const current = await getRelease();
  return fetch(publicUrl(current ? `data/${current.path}/${path.slice(5)}` : path));
}
