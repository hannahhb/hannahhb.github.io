const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
function app() {
  const document = { getElementById(id) {
    const match = html.match(new RegExp('id="' + id + '">(.*?)</script>', 's'));
    return { textContent: match ? match[1] : '' };
  }};
  const c = { window: { AtlasGeocoder: { create() { return { enabled:false }; } } }, document, localStorage: { getItem() { return 'test'; } }, URL,
    nodes: JSON.parse(document.getElementById('atlas-data').textContent).projects,
    geocoderAttribution() { return ''; }, apply() {}, drawGlobe() {}, mode: 'globe', panelMode: 'globe', sel: null,
    globePanel() { c.panelUpdates++; }, showPlace(pl) { c.selectedPlace = pl; }, panelUpdates: 0 };
  vm.createContext(c);
  vm.runInContext(html.slice(html.indexOf('function parseCSV'), html.indexOf('var rosterFile')), c);
  vm.runInContext(html.slice(html.indexOf('var cityGeocoder ='), html.indexOf('/* The published Google Sheet')), c);
  return c;
}
test('a synthetic topology signup in Lenoir, NC is placed in North Carolina', () => {
  const c = app();
  const csv = 'Full Name,Project Name,"Location (City, Country)",Email Address\n' +
    'Test Participant,Topological Signatures of Deception: Comparing Persistent Homology with Linear Probes,"lenoir, nc",private@example.test';
  const entries = c.csvEntries(csv);
  assert.equal(entries.length, 1);
  assert.equal(entries[0].email, undefined);
  c.setEntries(entries);
  const place = Object.values(c.places)[0];
  assert.equal(place.label, 'Lenoir, United States');
  assert.ok(Math.abs(place.lat - 35.91402) < 0.01);
  assert.ok(Math.abs(place.lon + 81.53898) < 0.01);
});
test('US state suffixes do not become similarly named countries', () => {
  const c = app();
  for (const location of ['lenoir, nc', 'Lenoir, North Carolina', 'Lenoir, NC, USA']) {
    assert.equal(c.geocode(location).label, 'Lenoir, United States');
  }
  assert.equal(c.geocode('Unknown Town, NC').label, 'United States');
  assert.equal(c.geocode('Unknown Town, NC').approx, true);
  assert.equal(c.geocode('NC').label, 'New Caledonia');
  assert.equal(c.geocode('Melbourne, Australia').label, 'Melbourne, Australia');
  assert.equal(c.geocode('Unknown Town'), null);
});
test('the open globe panel refreshes when signups arrive', () => {
  const c = app();
  c.setEntries([{ projectId: c.nodes[0].id, name: 'Test Participant', location: 'Melbourne' }]);
  assert.equal(c.panelUpdates, 1);
});
test('a selected place receives the updated roster without losing selection', () => {
  const c = app();
  c.selPlace = 'Lenoir, United States';
  c.setEntries([{ projectId: c.nodes[0].id, name: 'New Participant', location: 'lenoir, nc' }]);
  assert.equal(c.selectedPlace.people[0].name, 'New Participant');
  assert.equal(c.panelUpdates, 0);
});
test('explicit countries constrain city matches', () => {
  const c = app();
  const place = c.geocode('Lenoir, France');
  assert.equal(place.label, 'France');
  assert.equal(place.approx, true);
});

test('late geocoder results cannot restore an old roster', async () => {
  const c = app();
  let finish;
  c.cityGeocoder = { enabled:true, lookup:()=>new Promise(resolve=>{finish=resolve;}), best:r=>r[0] };
  const earlier=c.setEntries([{projectId:c.nodes[0].id,name:'Old',location:'Lenoir'}]);
  await c.setEntries([]);
  finish([{lat:35.9,lon:-81.5,label:'Lenoir, North Carolina'}]);
  await earlier;
  assert.equal(c.rosterCount,0);
  assert.equal(Object.keys(c.places).length,0);
});
test('provider coordinates replace an offline match; unavailable service preserves fallback', async () => {
  const c=app();
  c.cityGeocoder={enabled:true,lookup:async()=>[{lat:35.9,lon:-81.5,label:'Lenoir, North Carolina'}],best:r=>r[0]};
  const rows=[{projectId:c.nodes[0].id,name:'Test',location:'lenoir, nc'}];
  await c.setEntries(rows);
  assert.equal(Object.values(c.places)[0].label,'Lenoir, North Carolina');
  c.cityGeocoder.lookup=async()=>{throw new Error('offline');};
  await c.setEntries(rows);
  assert.equal(Object.values(c.places)[0].label,'Lenoir, United States');
});
