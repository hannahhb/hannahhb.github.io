const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const context = { URL, URLSearchParams, AbortController, setTimeout, clearTimeout };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../geocoder.js'), 'utf8'), context);
const { create } = context.AtlasGeocoder;
const city = { city:'Lenoir', state:'North Carolina', country:'United States of America',
  lat:35.91402, lon:-81.53898, result_type:'city', rank:{ confidence:1 } };
const ok = (results = [city]) => ({ok:true, json:async () => ({results})});
function client(fetch, extra = {}) { return create({apiKey:'test-only', fetch, interval:0, storage:null, ...extra}); }
test('city lookup encodes text and sends no identity fields; duplicate requests coalesce', async () => {
  const calls = [];
  const c = client(async url => { calls.push(new URL(url)); return ok(); });
  const [a, b] = await Promise.all([c.lookup('lenoir, nc'), c.lookup('LENOIR, NC')]);
  assert.equal(calls.length, 1);
  assert.equal(a[0].label, 'Lenoir, North Carolina, United States of America');
  assert.deepEqual(a,b);
  assert.equal(calls[0].searchParams.get('type'), 'city');
  assert.equal(calls[0].searchParams.get('text'), 'lenoir, nc');
  assert.deepEqual([...calls[0].searchParams.keys()].sort(), ['apiKey','bias','format','lang','limit','text','type']);
});
test('cached results survive reload without another paid lookup', async () => {
  let data, requests = 0;
  const storage = { getItem:() => data, setItem:(k,v) => { data = v; } };
  const fetch = async () => { requests++; return ok(); };
  await client(fetch, {storage}).lookup('Lenoir, NC');
  const results = await client(fetch, {storage}).lookup('Lenoir, NC');
  assert.equal(requests,1);
  assert.equal(results[0].lat,city.lat);
  assert.ok(!data.includes('test-only'));
});
test('no key makes no requests', async () => {
  const c = client(() => { throw new Error('must not call'); }, {apiKey:''});
  assert.equal((await c.lookup('Lenoir, NC')).length, 0);
});
test('quota failures do not cause a request for every queued location or poison storage', async () => {
  let requests=0, writes=0;
  const c=client(async () => { requests++; return {ok:false,status:429}; },
    {storage:{getItem:()=>null,setItem:()=>writes++}});
  const outcomes = await Promise.allSettled([c.lookup('Lenoir'), c.lookup('London')]);
  assert.ok(outcomes.every(o=>o.status==='rejected'));
  assert.equal(requests,1); assert.equal(writes,0);
});
test('malformed and non-city coordinates never become pins', async () => {
  const c = client(async () => ok([{...city,lat:999},{...city,lon:'-81'},
    {...city,result_type:'building'}]));
  assert.equal((await c.lookup('bad')).length, 0);
});
test('ambiguous and low-confidence responses are not chosen automatically', async () => {
  const c = client(async () => ok([city,{...city,city:'Another Lenoir'}]));
  assert.equal(c.best(await c.lookup('Lenoir')),null);
  assert.equal(c.best([{...city,label:'Uncertain',confidence:0.4}]),null);
});
test('a timed-out request releases the queue', async () => {
  const c = client((url, {signal}) => new Promise((resolve,reject) =>
    signal.addEventListener('abort',()=>reject(new Error('aborted')))), {timeout:5});
  await assert.rejects(c.lookup('Lenoir'), /aborted/);
  await assert.rejects(c.lookup('London'), /temporarily unavailable/);
});
