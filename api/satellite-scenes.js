// Public, read-only catalogue lookup. No credentials or arbitrary upstream URLs.
const STAC = 'https://planetarycomputer.microsoft.com/api/stac/v1/search';
const BBOX = [53.4, 17.5, 54.3, 18.5];
const TRUSTED = require('../app/src/data/trustedSatelliteHosts.json');
const MAX_BYTES = 1024 * 1024;

function httpsUrl(value, hosts) {
  if (typeof value !== 'string' || value.length > 4096) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password && !url.port
      && hosts.includes(url.hostname) ? url.href : null;
  } catch { return null; }
}

async function boundedJson(response) {
  if (Number(response.headers.get('content-length')) > MAX_BYTES) throw new Error('Catalogue response too large');
  if (!response.body) throw new Error('Empty catalogue response');
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) { await reader.cancel(); throw new Error('Catalogue response too large'); }
      chunks.push(Buffer.from(value));
    }
  } finally { reader.releaseLock(); }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
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
    redirect: 'error',
  });
  if (!response.ok) throw new Error(`Catalogue returned ${response.status}`);
  const doc = await boundedJson(response);
  if (!doc || !Array.isArray(doc.features) || doc.features.length > 1000) throw new Error('Invalid catalogue response');
  const seen = new Set();
  const scenes = doc.features.filter((f) => {
    if (!f || typeof f.properties?.datetime !== 'string') return false;
    const time = Date.parse(f.properties.datetime);
    if (typeof f.id !== 'string' || f.id.length > 256 || seen.has(f.id) || !Number.isFinite(time) || time > now.getTime() || time < start.getTime()) return false;
    seen.add(f.id); return true;
  }).map((f) => {
    const p = f.properties;
    const preview = httpsUrl(f.assets?.rendered_preview?.href, TRUSTED.preview) || httpsUrl(f.assets?.preview?.href, TRUSTED.preview);
    return {
      id: f.id, datetime: new Date(p.datetime).toISOString(), date: new Date(p.datetime).toISOString().slice(0, 10),
      cloudCover: Number.isFinite(p['eo:cloud_cover']) && p['eo:cloud_cover'] >= 0 && p['eo:cloud_cover'] <= 100 ? p['eo:cloud_cover'] : null,
      tile: typeof p['s2:mgrs_tile'] === 'string' && /^[0-9A-Z]{5,6}$/.test(p['s2:mgrs_tile']) ? p['s2:mgrs_tile'] : null,
      collection: 'sentinel-2-l2a', previewUrl: preview,
      selfHref: httpsUrl(Array.isArray(f.links) ? f.links.find((link) => link?.rel === 'self')?.href : null, TRUSTED.catalogue),
    };
  }).sort((a, b) => b.datetime.localeCompare(a.datetime)).slice(0, 6);
  return { scenes, checkedAt: now.toISOString(), newestCapture: scenes[0]?.datetime || null, source: 'Microsoft Planetary Computer / Sentinel-2 L2A', lookbackDays: 60, cloudCoverBelow: 30 };
}

function createHandler(search = searchScenes, clock = Date.now) {
  let cached, expires = 0, pending, retryAt = 0;
  return async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed' });
  }
  // This fixed public lookup accepts no user-selected URL, region, or query.
  if ((req.url || '').length > 2048 || (req.url || '').includes('?')) {
    return res.status(400).json({ error: 'query_not_supported' });
  }
  if (req.headers?.['sec-fetch-site'] === 'cross-site') {
    return res.status(403).json({ error: 'cross_site_request_rejected' });
  }
  if (clock() < retryAt) {
    res.setHeader('Retry-After', String(Math.max(1, Math.ceil((retryAt - clock()) / 1000))));
    return res.status(503).json({ error: 'satellite_source_unavailable' });
  }
  try {
    if (!cached || clock() >= expires) {
      if (!pending) pending = Promise.resolve().then(search).then(result => {
        cached = result; expires = clock() + 60000; return result;
      }).catch(error => { retryAt = clock() + 15000; throw error; }).finally(() => { pending = undefined; });
      await pending;
    }
    res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate');
    res.setHeader('Vercel-CDN-Cache-Control', 'public, s-maxage=60');
    res.setHeader('Vary', 'Sec-Fetch-Site');
    return res.status(200).json(cached);
  } catch (error) {
    console.error('Satellite catalogue lookup failed');
    return res.status(502).json({ error: 'satellite_source_unavailable' });
  }
  };
}
const handler = createHandler();
module.exports = handler;
module.exports.searchScenes = searchScenes;
module.exports.createHandler = createHandler;
