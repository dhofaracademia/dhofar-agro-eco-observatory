const {test} = require('node:test');
const assert = require('node:assert/strict');
const handler = require('../api/satellite-scenes.js');
const {searchScenes} = handler;
const reply = (doc, status=200) => new Response(JSON.stringify(doc), { status, headers: {'Content-Type':'application/json'} });
const now = new Date('2026-09-23T12:00:00Z');
const feature = (id, date, preview='https://example.com/preview.jpg') => ({id,properties:{datetime:date,'eo:cloud_cover':2,'s2:mgrs_tile':'39QYA'},assets:{rendered_preview:{href:preview}}});
test('requests fixed area and dates; sorts and deduplicates real scenes',async()=>{
 const result=await searchScenes(async(url,options)=>{
  assert.equal(url,'https://planetarycomputer.microsoft.com/api/stac/v1/search');
  const body=JSON.parse(options.body);assert.equal(body.limit,6);assert.deepEqual(body.bbox,[53.4,17.5,54.3,18.5]);
  return reply({features:[feature('a','2026-09-20T10:00:00Z'),feature('b','2026-09-22T10:00:00Z'),feature('b','2026-09-22T10:00:00Z'),feature('future','2026-10-01T10:00:00Z'),feature('old','2025-01-01T10:00:00Z')]});
 },now);
 assert.deepEqual(result.scenes.map(s=>s.id),['b','a']);assert.equal(result.checkedAt,now.toISOString());assert.equal(result.newestCapture,'2026-09-22T10:00:00.000Z');
});
test('empty catalogue is success, malformed response and upstream failure are errors',async()=>{
 assert.deepEqual((await searchScenes(async()=>reply({features:[]}),now)).scenes,[]);
 await assert.rejects(searchScenes(async()=>reply({},503),now));
 await assert.rejects(searchScenes(async()=>reply({}),now));
});
test('untrusted URL schemes never become image sources',async()=>{
 const result=await searchScenes(async()=>reply({features:[feature('a','2026-09-20T10:00:00Z','javascript:alert(1)')]}),now);
 assert.equal(result.scenes[0].previewUrl,null);
});
test('handler rejects mutation methods',async()=>{
 const res={headers:{},setHeader(k,v){this.headers[k]=v},status(n){this.code=n;return this},json(d){this.body=d;return this}};
 await handler({method:'POST'},res);assert.equal(res.code,405);assert.equal(res.headers.Allow,'GET');
});

test('rejects untrusted hosts, lookalikes, credentials and nonstandard ports', async () => {
  for (const url of ['https://attacker.invalid/p.png', 'https://planetarycomputer.microsoft.com.attacker.invalid/p.png',
    'https://planetarycomputer.microsoft.com@attacker.invalid/p.png', 'https://user:pass@planetarycomputer.microsoft.com/p.png',
    'https://planetarycomputer.microsoft.com:8443/p.png', 'http://planetarycomputer.microsoft.com/p.png']) {
    const result = await searchScenes(async () => reply({ features: [feature('a','2026-09-20T10:00:00Z',url)] }), now);
    assert.equal(result.scenes[0].previewUrl, null);
  }
  const url = 'https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png';
  const result = await searchScenes(async () => reply({ features: [feature('a','2026-09-20T10:00:00Z',url)] }), now);
  assert.equal(result.scenes[0].previewUrl, url);
});

test('bounds upstream responses and tolerates malformed individual records', async () => {
  await assert.rejects(searchScenes(async () => new Response('x'.repeat(1024 * 1024 + 1)), now), /too large/);
  await assert.rejects(searchScenes(async () => reply(null), now), /Invalid/);
  const result = await searchScenes(async () => reply({features: [null, {}, {id:'bad',properties:{datetime:8}},
    {...feature('valid','2026-09-20T10:00:00Z'),links:{not:'an array'}}]}), now);
  assert.deepEqual(result.scenes.map(s => s.id), ['valid']);
});

const response = () => ({headers:{},setHeader(k,v){this.headers[k]=v},status(n){this.code=n;return this},json(d){this.body=d;return this}});
test('rejects unsupported query input and cross-site browser requests without upstream calls', async () => {
  let calls = 0;
  const api = handler.createHandler(async () => { calls++; return {}; });
  for (const req of [{method:'GET',url:'/api/satellite-scenes?url=https://127.0.0.1'},
    {method:'GET',headers:{'sec-fetch-site':'cross-site'}}, {method:'DELETE'}]) {
    const res = response(); await api(req,res); assert.ok(res.code >= 400);
    assert.equal(res.headers['Cache-Control'], 'no-store');
  }
  assert.equal(calls,0);
});

test('concurrent requests share one lookup, use a bounded TTL and do not cache errors', async () => {
  let calls=0, time=1000;
  const api = handler.createHandler(async () => { calls++; return {scenes:[],checkedAt:'test'}; }, () => time);
  const responses=Array.from({length:12},response);
  await Promise.all(responses.map(res=>api({method:'GET'},res)));
  assert.equal(calls,1);
  assert.ok(responses.every(r=>r.code===200 && r.headers['Vercel-CDN-Cache-Control'].includes('s-maxage=60')));
  time+=60001; await api({method:'GET'},response()); assert.equal(calls,2);
  let failures=0;
  const broken=handler.createHandler(async()=>{failures++;throw new Error('private upstream detail')},()=>time);
  const first=response();await broken({method:'GET'},first);assert.equal(first.code,502);
  assert.ok(!JSON.stringify(first.body).includes('private'));
  const next=response();await broken({method:'GET'},next);assert.equal(next.code,503);
  assert.equal(failures,1);assert.equal(next.headers['Cache-Control'],'no-store');
  assert.equal(next.headers['Retry-After'],'15');
});
