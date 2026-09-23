const {test} = require('node:test');
const assert = require('node:assert/strict');
const handler = require('../api/satellite-scenes.js');
const {searchScenes} = handler;
const now = new Date('2026-09-23T12:00:00Z');
const feature = (id, date, preview='https://example.com/preview.jpg') => ({id,properties:{datetime:date,'eo:cloud_cover':2,'s2:mgrs_tile':'39QYA'},assets:{rendered_preview:{href:preview}}});
test('requests fixed area and dates; sorts and deduplicates real scenes',async()=>{
 const result=await searchScenes(async(url,options)=>{
  assert.equal(url,'https://planetarycomputer.microsoft.com/api/stac/v1/search');
  const body=JSON.parse(options.body);assert.equal(body.limit,6);assert.deepEqual(body.bbox,[53.4,17.5,54.3,18.5]);
  return {ok:true,json:async()=>({features:[feature('a','2026-09-20T10:00:00Z'),feature('b','2026-09-22T10:00:00Z'),feature('b','2026-09-22T10:00:00Z'),feature('future','2026-10-01T10:00:00Z'),feature('old','2025-01-01T10:00:00Z')]})};
 },now);
 assert.deepEqual(result.scenes.map(s=>s.id),['b','a']);assert.equal(result.checkedAt,now.toISOString());assert.equal(result.newestCapture,'2026-09-22T10:00:00Z');
});
test('empty catalogue is success, malformed response and upstream failure are errors',async()=>{
 assert.deepEqual((await searchScenes(async()=>({ok:true,json:async()=>({features:[]})}),now)).scenes,[]);
 await assert.rejects(searchScenes(async()=>({ok:false,status:503}),now));
 await assert.rejects(searchScenes(async()=>({ok:true,json:async()=>({})}),now));
});
test('untrusted URL schemes never become image sources',async()=>{
 const result=await searchScenes(async()=>({ok:true,json:async()=>({features:[feature('a','2026-09-20T10:00:00Z','javascript:alert(1)')]})}),now);
 assert.equal(result.scenes[0].previewUrl,null);
});
test('handler rejects mutation methods',async()=>{
 const res={headers:{},setHeader(k,v){this.headers[k]=v},status(n){this.code=n;return this},json(d){this.body=d;return this}};
 await handler({method:'POST'},res);assert.equal(res.code,405);assert.equal(res.headers.Allow,'GET');
});
