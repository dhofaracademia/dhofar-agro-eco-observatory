// Public, read-only catalogue lookup. No credentials or arbitrary upstream URLs.
const STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1/search';
const BBOX = [53.4, 17.5, 54.3, 18.5];

function httpsUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' ? url.href : null;
  } catch { return null; }
}

async function searchScenes(fetcher = fetch, now = new Date()) {
  const start = new Date(now.getTime() - 60 * 86400000);
  const response = await fetcher(STAC, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/geo+json' },
    body: JSON.stringify({
      collections: ['sentinel-2-l2a'], bbox: BBOX,
      datetime: `${start.toISOString()}/${now.toISOString()}`,
      query: { 'eo:cloud_cover': { lt: 30 } },
      limit: 6, sortby: [{ field: 'datetime', direction: 'desc' }],
    }),
    signal: AbortSignal.timeout(18000),
  });
  if (!response.ok) throw new Error(`Catalogue returned ${response.status}`);
  const doc = await response.json();
  if (!Array.isArray(doc.features)) throw new Error('Invalid catalogue response');
  const seen = new Set();
  const scenes = doc.features.filter((f) => {
    const time = Date.parse(f.properties?.datetime);
    if (typeof f.id !== 'string' || seen.has(f.id) || !Number.isFinite(time) || time > now.getTime() || time < start.getTime()) return false;
    seen.add(f.id); return true;
  }).map((f) => {
    const p = f.properties;
    const preview = httpsUrl(f.assets?.rendered_preview?.href) || httpsUrl(f.assets?.preview?.href);
    return {
      id: f.id, datetime: p.datetime, date: p.datetime.slice(0, 10),
      cloudCover: typeof p['eo:cloud_cover'] === 'number' ? p['eo:cloud_cover'] : null,
      tile: typeof p['s2:mgrs_tile'] === 'string' ? p['s2:mgrs_tile'] : null,
      collection: 'sentinel-2-l2a', previewUrl: preview,
      selfHref: httpsUrl(f.links?.find((link) => link.rel === 'self')?.href),
    };
  }).sort((a, b) => b.datetime.localeCompare(a.datetime)).slice(0, 6);
  return { scenes, checkedAt: now.toISOString(), newestCapture: scenes[0]?.datetime || null, source: 'Microsoft Planetary Computer / Sentinel-2 L2A', lookbackDays: 60, cloudCoverBelow: 30 };
}

async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed' });
  }
  try {
    return res.status(200).json(await searchScenes());
  } catch (error) {
    console.error('Satellite catalogue lookup failed:', error.name, error.message);
    return res.status(502).json({ error: 'satellite_source_unavailable' });
  }
}
module.exports = handler;
module.exports.searchScenes = searchScenes;
